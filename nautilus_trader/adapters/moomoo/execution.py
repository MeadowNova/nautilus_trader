# -------------------------------------------------------------------------------------------------
#  Moomoo Execution Client for NautilusTrader
#  Provides order execution with rate limiting and risk management
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from moomoo import OpenSecTradeContext, TrdEnv, TrdSide, OrderType as MoomooOrderType, RET_OK, TrdMarket

from nautilus_trader.adapters.moomoo.common import MOOMOO_VENUE, ORDER_RATE_LIMIT
from nautilus_trader.adapters.moomoo.config import MoomooExecClientConfig
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.core.datetime import unix_nanos_to_dt
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.messages import (
    CancelOrder,
    ModifyOrder,
    SubmitOrder,
    SubmitOrderList,
)
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.model.enums import (
    AccountType,
    LiquiditySide,
    OmsType,
    OrderSide,
    OrderStatus,
    OrderType,
)
from nautilus_trader.model.events import (
    OrderAccepted,
    OrderCanceled,
    OrderFilled,
    OrderRejected,
    OrderSubmitted,
)
from nautilus_trader.execution.reports import OrderStatusReport, FillReport, PositionStatusReport
from nautilus_trader.model.enums import PositionSide
from nautilus_trader.model.identifiers import (
    AccountId,
    ClientId,
    ClientOrderId,
    InstrumentId,
    TradeId,
    VenueOrderId,
)
from nautilus_trader.model.objects import Money, Price, Quantity

if TYPE_CHECKING:
    from nautilus_trader.adapters.moomoo.providers import MoomooInstrumentProvider
    from risk_management_framework import PositionRiskConfig, PortfolioRiskConfig


@dataclass
class RateLimiter:
    """Rate limiter for order submission (15 orders per 30 seconds)."""

    max_orders: int = 15
    window_seconds: int = 30
    _timestamps: deque = field(default_factory=deque)

    def can_submit(self) -> bool:
        """Check if an order can be submitted within rate limits."""
        now = time.time()

        # Remove timestamps older than window
        while self._timestamps and self._timestamps[0] < now - self.window_seconds:
            self._timestamps.popleft()

        return len(self._timestamps) < self.max_orders

    def record_submission(self) -> None:
        """Record an order submission."""
        self._timestamps.append(time.time())

    def orders_remaining(self) -> int:
        """Get number of orders remaining in current window."""
        now = time.time()
        while self._timestamps and self._timestamps[0] < now - self.window_seconds:
            self._timestamps.popleft()
        return max(0, self.max_orders - len(self._timestamps))


@dataclass
class OrderTrackingData:
    """Track order state and fills."""

    client_order_id: ClientOrderId
    instrument_id: InstrumentId
    venue_order_id: VenueOrderId | None = None
    status: OrderStatus = OrderStatus.INITIALIZED
    submitted_time: int = 0
    filled_qty: Decimal = Decimal(0)
    avg_fill_price: Decimal = Decimal(0)
    last_update_time: int = 0


class MoomooExecClient(LiveExecutionClient):
    """
    Provides an execution client for Moomoo using OpenD gateway.

    Implements:
    - Order submission with rate limiting (15 per 30s)
    - Pre-trade risk checks with veto capability
    - Position tracking and reconciliation
    - Paper trading mode (TrdEnv.SIMULATE)
    - Emergency liquidation capability

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    instrument_provider : MoomooInstrumentProvider
        The instrument provider.
    config : MoomooExecClientConfig
        The configuration for the client.
    name : str | None
        The custom client ID.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: MoomooInstrumentProvider,
        config: MoomooExecClientConfig,
        name: str | None = None,
        position_risk_config: PositionRiskConfig | None = None,
        portfolio_risk_config: PortfolioRiskConfig | None = None,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=ClientId(name or f"{MOOMOO_VENUE.value}-EXEC"),
            venue=MOOMOO_VENUE,
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            base_currency=None,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            config=config,
        )

        self._config = config
        self._market = config.filter_trd_market  # Use filter_trd_market from exec config

        # Trading context
        self._trd_ctx: OpenSecTradeContext | None = None
        self._account_id: AccountId | None = None

        # Rate limiting
        self._rate_limiter = RateLimiter(
            max_orders=config.max_orders_per_30s,
            window_seconds=30,
        )

        # Order tracking
        self._orders: dict[ClientOrderId, OrderTrackingData] = {}
        self._venue_to_client: dict[str, ClientOrderId] = {}

        # Risk configuration
        self._position_risk_config = position_risk_config
        self._portfolio_risk_config = portfolio_risk_config
        self._emergency_liquidation_mode = False

        # Submission lock
        self._submission_lock = asyncio.Lock()

    async def _connect(self) -> None:
        """Connect to Moomoo OpenD gateway for trading."""
        self._log.info(
            f"Connecting to Moomoo OpenD for trading at "
            f"{self._config.gateway.host}:{self._config.gateway.port}..."
        )

        try:
            # Determine trading environment
            trd_env = TrdEnv.SIMULATE if self._config.gateway.trading_mode == "paper" else TrdEnv.REAL

            # Map market string to TrdMarket enum
            market_map = {
                "US": TrdMarket.US,
                "HK": TrdMarket.HK,
                "CN": TrdMarket.CN,
                "SG": TrdMarket.SG,
            }
            trd_market = market_map.get(self._config.filter_trd_market, TrdMarket.US)

            # Create trade context
            self._trd_ctx = OpenSecTradeContext(
                filter_trdmarket=trd_market,
                host=self._config.gateway.host,
                port=self._config.gateway.port,
            )

            # Unlock trading if password provided (required for live)
            if self._config.gateway.unlock_password:
                ret, data = self._trd_ctx.unlock_trade(self._config.gateway.unlock_password)
                if ret != RET_OK:
                    self._log.warning(f"Trade unlock failed: {data}")

            # Get account list
            ret, acc_list = self._trd_ctx.get_acc_list()
            if ret != RET_OK:
                raise ConnectionError(f"Failed to get account list: {acc_list}")

            # Find paper trading account
            for _, row in acc_list.iterrows():
                acc_id = str(row.get('acc_id', ''))
                trd_env_val = row.get('trd_env', '')

                if trd_env == TrdEnv.SIMULATE and 'SIMULATE' in str(trd_env_val):
                    self._account_id = AccountId(f"MOOMOO-{acc_id}")
                    break
                elif trd_env == TrdEnv.REAL and 'REAL' in str(trd_env_val):
                    self._account_id = AccountId(f"MOOMOO-{acc_id}")
                    break

            if self._account_id is None and len(acc_list) > 0:
                acc_id = str(acc_list.iloc[0]['acc_id'])
                self._account_id = AccountId(f"MOOMOO-{acc_id}")

            self._log.info(f"Connected to Moomoo trading. Account: {self._account_id}")

            # Generate initial account state
            await self._request_account_state()

        except Exception as e:
            self._log.error(f"Connection failed: {e}")
            raise

    async def _disconnect(self) -> None:
        """Disconnect from Moomoo trading."""
        self._log.info("Disconnecting from Moomoo trading...")

        if self._trd_ctx:
            self._trd_ctx.close()
            self._trd_ctx = None

        self._orders.clear()
        self._venue_to_client.clear()

        self._log.info("Moomoo execution client disconnected")

    async def _request_account_state(self) -> None:
        """Request and publish account state."""
        if self._trd_ctx is None:
            return

        try:
            ret, data = self._trd_ctx.accinfo_query()
            if ret == RET_OK and data is not None and not data.empty:
                row = data.iloc[0]
                cash = float(row.get('cash', 0) or 0)
                market_val = float(row.get('market_val', 0) or 0)
                total_assets = float(row.get('total_assets', 0) or 0)

                self._log.info(
                    f"Account State: Cash=${cash:,.2f}, "
                    f"Market Value=${market_val:,.2f}, "
                    f"Total=${total_assets:,.2f}"
                )
        except Exception as e:
            self._log.error(f"Failed to get account state: {e}")

    def _to_moomoo_code(self, instrument_id: InstrumentId) -> str:
        """Convert InstrumentId to Moomoo code format."""
        symbol = instrument_id.symbol.value
        if "." in symbol:
            return symbol
        return f"{self._market}.{symbol}"

    def _check_pre_trade_risk(self, command: SubmitOrder) -> tuple[bool, str]:
        """
        Perform pre-trade risk checks.

        Returns (True, "") if order passes, (False, reason) if vetoed.
        """
        order = command.order

        # Check emergency liquidation mode
        if self._emergency_liquidation_mode and order.side == OrderSide.BUY:
            return False, "Emergency liquidation mode active - BUY orders blocked"

        # Check rate limit
        if not self._rate_limiter.can_submit():
            return False, f"Rate limit exceeded (max {ORDER_RATE_LIMIT} orders per 30s)"

        # Check position size limits if config provided
        if self._position_risk_config:
            # Get estimated order value
            price = float(order.price) if order.price else 100.0  # Fallback for market orders
            order_value = float(order.quantity) * price

            if order_value > self._position_risk_config.max_position_size_usd:
                return False, (
                    f"Order value ${order_value:,.0f} exceeds max "
                    f"${self._position_risk_config.max_position_size_usd:,.0f}"
                )

        return True, ""

    async def _submit_order(self, command: SubmitOrder) -> None:
        """Submit an order to Moomoo."""
        order = command.order

        async with self._submission_lock:
            # Pre-trade risk check
            passed, reason = self._check_pre_trade_risk(command)
            if not passed:
                self._log.warning(f"Order rejected by pre-trade risk check: {reason}")
                self._generate_order_rejected(order, reason)
                return

            if self._trd_ctx is None:
                self._generate_order_rejected(order, "Not connected to Moomoo")
                return

            try:
                # Record rate limit
                self._rate_limiter.record_submission()

                # Generate submitted event
                ts_now = self._clock.timestamp_ns()
                self._generate_order_submitted(order, ts_now)

                # Convert to Moomoo order parameters
                code = self._to_moomoo_code(order.instrument_id)
                trd_side = TrdSide.BUY if order.side == OrderSide.BUY else TrdSide.SELL

                # Map order type
                if order.order_type == OrderType.MARKET:
                    order_type = MoomooOrderType.MARKET
                    price = 0.0
                else:
                    order_type = MoomooOrderType.NORMAL
                    price = float(order.price) if order.price else 0.0

                qty = float(order.quantity)

                # Determine trading environment
                trd_env = TrdEnv.SIMULATE if self._config.gateway.trading_mode == "paper" else TrdEnv.REAL

                # Submit order
                ret, data = self._trd_ctx.place_order(
                    price=price,
                    qty=qty,
                    code=code,
                    trd_side=trd_side,
                    order_type=order_type,
                    trd_env=trd_env,
                )

                if ret == RET_OK and data is not None and not data.empty:
                    venue_order_id = str(data.iloc[0]['order_id'])

                    # Track the order
                    tracking = OrderTrackingData(
                        client_order_id=order.client_order_id,
                        instrument_id=order.instrument_id,
                        venue_order_id=VenueOrderId(venue_order_id),
                        status=OrderStatus.ACCEPTED,
                        submitted_time=ts_now,
                    )
                    self._orders[order.client_order_id] = tracking
                    self._venue_to_client[venue_order_id] = order.client_order_id

                    # Generate accepted event
                    self._generate_order_accepted(order, VenueOrderId(venue_order_id))

                    self._log.info(
                        f"Order submitted: {order.client_order_id} -> {venue_order_id}"
                    )

                else:
                    error_msg = str(data) if data is not None else "Unknown error"
                    self._generate_order_rejected(order, error_msg)
                    self._log.error(f"Order submission failed: {error_msg}")

            except Exception as e:
                self._generate_order_rejected(order, str(e))
                self._log.error(f"Order submission error: {e}")

    async def _submit_order_list(self, command: SubmitOrderList) -> None:
        """Submit a list of orders."""
        for order in command.order_list.orders:
            submit_cmd = SubmitOrder(
                trader_id=command.trader_id,
                strategy_id=command.strategy_id,
                order=order,
                position_id=command.position_id,
                command_id=UUID4(),
                ts_init=self._clock.timestamp_ns(),
            )
            await self._submit_order(submit_cmd)

    async def _cancel_order(self, command: CancelOrder) -> None:
        """Cancel an order."""
        if self._trd_ctx is None:
            self._log.error("Not connected to Moomoo")
            return

        order = self._cache.order(command.client_order_id)
        if order is None:
            self._log.warning(f"Order not found: {command.client_order_id}")
            return

        tracking = self._orders.get(command.client_order_id)
        if tracking is None or tracking.venue_order_id is None:
            self._log.warning(f"No venue order ID for: {command.client_order_id}")
            return

        try:
            trd_env = TrdEnv.SIMULATE if self._config.gateway.trading_mode == "paper" else TrdEnv.REAL

            ret, data = self._trd_ctx.modify_order(
                modify_order_op=2,  # Cancel
                order_id=tracking.venue_order_id.value,
                qty=0,
                price=0,
                trd_env=trd_env,
            )

            if ret == RET_OK:
                self._generate_order_canceled(order, tracking.venue_order_id)
                self._log.info(f"Order canceled: {command.client_order_id}")
            else:
                self._log.error(f"Cancel failed: {data}")

        except Exception as e:
            self._log.error(f"Cancel order error: {e}")

    async def _modify_order(self, command: ModifyOrder) -> None:
        """Modify an order (not fully implemented)."""
        self._log.warning("Order modification not fully implemented for Moomoo")

    def _generate_order_submitted(self, order, ts_event: int) -> None:
        """Generate and publish OrderSubmitted event."""
        event = OrderSubmitted(
            trader_id=order.trader_id,
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            account_id=self._account_id or AccountId("MOOMOO-UNKNOWN"),
            ts_event=ts_event,
            ts_init=ts_event,
        )
        self._msgbus.send(endpoint="ExecEngine.process", msg=event)

    def _generate_order_accepted(self, order, venue_order_id: VenueOrderId) -> None:
        """Generate and publish OrderAccepted event."""
        ts_now = self._clock.timestamp_ns()
        event = OrderAccepted(
            trader_id=order.trader_id,
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            venue_order_id=venue_order_id,
            account_id=self._account_id or AccountId("MOOMOO-UNKNOWN"),
            ts_event=ts_now,
            ts_init=ts_now,
        )
        self._msgbus.send(endpoint="ExecEngine.process", msg=event)

    def _generate_order_rejected(self, order, reason: str) -> None:
        """Generate and publish OrderRejected event."""
        ts_now = self._clock.timestamp_ns()
        event = OrderRejected(
            trader_id=order.trader_id,
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            account_id=self._account_id or AccountId("MOOMOO-UNKNOWN"),
            reason=reason,
            ts_event=ts_now,
            ts_init=ts_now,
        )
        self._msgbus.send(endpoint="ExecEngine.process", msg=event)

    def _generate_order_canceled(self, order, venue_order_id: VenueOrderId) -> None:
        """Generate and publish OrderCanceled event."""
        ts_now = self._clock.timestamp_ns()
        event = OrderCanceled(
            trader_id=order.trader_id,
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            venue_order_id=venue_order_id,
            account_id=self._account_id or AccountId("MOOMOO-UNKNOWN"),
            ts_event=ts_now,
            ts_init=ts_now,
        )
        self._msgbus.send(endpoint="ExecEngine.process", msg=event)

    def trigger_emergency_liquidation(self) -> None:
        """Trigger emergency liquidation mode - blocks new BUY orders."""
        self._emergency_liquidation_mode = True
        self._log.warning("EMERGENCY LIQUIDATION MODE ACTIVATED")

    def disable_emergency_liquidation(self) -> None:
        """Disable emergency liquidation mode."""
        self._emergency_liquidation_mode = False
        self._log.info("Emergency liquidation mode disabled")

    def get_rate_limit_status(self) -> dict:
        """Get current rate limit status."""
        return {
            "orders_remaining": self._rate_limiter.orders_remaining(),
            "max_orders": self._rate_limiter.max_orders,
            "window_seconds": self._rate_limiter.window_seconds,
        }

    async def generate_order_status_reports(
        self,
        instrument_id: InstrumentId | None = None,
        start: int | None = None,
        end: int | None = None,
        open_only: bool = False,
    ) -> list[OrderStatusReport]:
        """
        Generate order status reports from Moomoo for execution reconciliation.

        This method is called during startup reconciliation to sync with the venue.
        """
        if self._trd_ctx is None:
            self._log.warning("Cannot generate order status reports: not connected")
            return []

        try:
            # Query Moomoo for all orders
            trd_env = TrdEnv.SIMULATE if self._config.gateway.trading_mode == "paper" else TrdEnv.REAL
            ret, orders_df = self._trd_ctx.order_list_query(trd_env=trd_env)

            if ret != RET_OK:
                self._log.error(f"Order query failed: {orders_df}")
                return []

            if orders_df is None or orders_df.empty:
                self._log.debug("No orders found on Moomoo")
                return []

            reports = []
            for _, row in orders_df.iterrows():
                try:
                    code = str(row.get('code', ''))
                    if not code:
                        continue

                    order_id = str(row.get('order_id', ''))

                    # Build instrument_id from code
                    if "." in code:
                        _, symbol = code.split(".", 1)
                    else:
                        symbol = code
                    inst_id = InstrumentId.from_str(f"{symbol}.{MOOMOO_VENUE.value}")

                    # Filter by instrument if specified
                    if instrument_id is not None and inst_id != instrument_id:
                        continue

                    # Map Moomoo order status
                    moomoo_status = str(row.get('order_status', ''))
                    status_map = {
                        'SUBMITTED': OrderStatus.SUBMITTED,
                        'FILLED_ALL': OrderStatus.FILLED,
                        'FILLED_PART': OrderStatus.PARTIALLY_FILLED,
                        'CANCELLED_ALL': OrderStatus.CANCELED,
                        'CANCELLED_PART': OrderStatus.CANCELED,
                        'FAILED': OrderStatus.REJECTED,
                        'WAITING_SUBMIT': OrderStatus.INITIALIZED,
                    }
                    order_status = status_map.get(moomoo_status, OrderStatus.ACCEPTED)

                    # Skip non-open orders if open_only requested
                    if open_only and order_status not in (
                        OrderStatus.SUBMITTED,
                        OrderStatus.ACCEPTED,
                        OrderStatus.PARTIALLY_FILLED,
                    ):
                        continue

                    # Map order side
                    trd_side = str(row.get('trd_side', ''))
                    order_side = OrderSide.BUY if 'BUY' in trd_side else OrderSide.SELL

                    # Get quantities and prices
                    qty = int(row.get('qty', 0))
                    dealt_qty = int(row.get('dealt_qty', 0))
                    price = float(row.get('price', 0.0))

                    # Determine order type
                    order_type = OrderType.MARKET if price == 0 else OrderType.LIMIT

                    report = OrderStatusReport(
                        account_id=self._account_id or AccountId("MOOMOO-UNKNOWN"),
                        instrument_id=inst_id,
                        client_order_id=ClientOrderId(order_id),
                        venue_order_id=VenueOrderId(order_id),
                        order_side=order_side,
                        order_type=order_type,
                        order_status=order_status,
                        price=Price.from_str(str(price)) if price > 0 else None,
                        quantity=Quantity.from_str(str(qty)),
                        filled_qty=Quantity.from_str(str(dealt_qty)),
                        ts_last=self._clock.timestamp_ns(),
                        ts_init=self._clock.timestamp_ns(),
                    )
                    reports.append(report)

                except Exception as e:
                    self._log.error(f"Error processing order row: {e}")
                    continue

            self._log.info(f"Generated {len(reports)} order status reports")
            return reports

        except Exception as e:
            self._log.error(f"Error generating order status reports: {e}")
            return []

    async def generate_fill_reports(
        self,
        instrument_id: InstrumentId | None = None,
        venue_order_id: VenueOrderId | None = None,
        start: int | None = None,
        end: int | None = None,
    ) -> list[FillReport]:
        """
        Generate fill reports from Moomoo for execution reconciliation.
        """
        if self._trd_ctx is None:
            self._log.warning("Cannot generate fill reports: not connected")
            return []

        try:
            trd_env = TrdEnv.SIMULATE if self._config.gateway.trading_mode == "paper" else TrdEnv.REAL
            ret, deals_df = self._trd_ctx.deal_list_query(trd_env=trd_env)

            if ret != RET_OK:
                self._log.error(f"Deal query failed: {deals_df}")
                return []

            if deals_df is None or deals_df.empty:
                self._log.debug("No fills found on Moomoo")
                return []

            reports = []
            for _, row in deals_df.iterrows():
                try:
                    code = str(row.get('code', ''))
                    if not code:
                        continue

                    # Build instrument_id
                    if "." in code:
                        _, symbol = code.split(".", 1)
                    else:
                        symbol = code
                    inst_id = InstrumentId.from_str(f"{symbol}.{MOOMOO_VENUE.value}")

                    if instrument_id is not None and inst_id != instrument_id:
                        continue

                    trade_id = TradeId(str(row.get('deal_id', '')))
                    order_id = str(row.get('order_id', ''))

                    if venue_order_id is not None and order_id != venue_order_id.value:
                        continue

                    filled_qty = int(row.get('qty', 0))
                    filled_price = float(row.get('price', 0.0))
                    trd_side = str(row.get('trd_side', ''))
                    order_side = OrderSide.BUY if 'BUY' in trd_side else OrderSide.SELL

                    report = FillReport(
                        account_id=self._account_id or AccountId("MOOMOO-UNKNOWN"),
                        instrument_id=inst_id,
                        client_order_id=ClientOrderId(order_id),
                        venue_order_id=VenueOrderId(order_id),
                        trade_id=trade_id,
                        order_side=order_side,
                        last_qty=Quantity.from_str(str(filled_qty)),
                        last_px=Price.from_str(str(filled_price)),
                        commission=Money.from_str("0 USD"),
                        liquidity_side=LiquiditySide.TAKER,
                        ts_event=self._clock.timestamp_ns(),
                        ts_init=self._clock.timestamp_ns(),
                    )
                    reports.append(report)

                except Exception as e:
                    self._log.error(f"Error processing deal row: {e}")
                    continue

            self._log.info(f"Generated {len(reports)} fill reports")
            return reports

        except Exception as e:
            self._log.error(f"Error generating fill reports: {e}")
            return []

    async def generate_position_status_reports(
        self,
        instrument_id: InstrumentId | None = None,
        start: int | None = None,
        end: int | None = None,
    ) -> list[PositionStatusReport]:
        """
        Generate position status reports from Moomoo for execution reconciliation.
        """
        if self._trd_ctx is None:
            self._log.warning("Cannot generate position status reports: not connected")
            return []

        try:
            trd_env = TrdEnv.SIMULATE if self._config.gateway.trading_mode == "paper" else TrdEnv.REAL
            ret, positions_df = self._trd_ctx.position_list_query(trd_env=trd_env)

            if ret != RET_OK:
                self._log.error(f"Position query failed: {positions_df}")
                return []

            if positions_df is None or positions_df.empty:
                self._log.debug("No open positions found on Moomoo")
                return []

            reports = []
            for _, row in positions_df.iterrows():
                try:
                    code = str(row.get('code', ''))
                    if not code:
                        continue

                    # Build instrument_id
                    if "." in code:
                        _, symbol = code.split(".", 1)
                    else:
                        symbol = code
                    inst_id = InstrumentId.from_str(f"{symbol}.{MOOMOO_VENUE.value}")

                    if instrument_id is not None and inst_id != instrument_id:
                        continue

                    quantity = int(row.get('qty', 0))
                    if quantity == 0:
                        continue

                    position_side = PositionSide.LONG if quantity > 0 else PositionSide.SHORT

                    report = PositionStatusReport(
                        account_id=self._account_id or AccountId("MOOMOO-UNKNOWN"),
                        instrument_id=inst_id,
                        position_side=position_side,
                        quantity=Quantity.from_str(str(abs(quantity))),
                        ts_last=self._clock.timestamp_ns(),
                        ts_init=self._clock.timestamp_ns(),
                    )
                    reports.append(report)

                except Exception as e:
                    self._log.error(f"Error processing position row: {e}")
                    continue

            self._log.info(f"Generated {len(reports)} position status reports")
            return reports

        except Exception as e:
            self._log.error(f"Error generating position status reports: {e}")
            return []
