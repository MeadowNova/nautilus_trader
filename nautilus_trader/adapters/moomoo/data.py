# -------------------------------------------------------------------------------------------------
#  Moomoo Data Client for NautilusTrader
#  Provides real-time market data from Moomoo OpenD API
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd
from moomoo import OpenQuoteContext, RET_OK, SubType

from nautilus_trader.adapters.moomoo.common import MOOMOO_VENUE
from nautilus_trader.adapters.moomoo.config import MoomooDataClientConfig
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.core.datetime import dt_to_unix_nanos, unix_nanos_to_dt
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.data.messages import SubscribeBars, SubscribeQuoteTicks, SubscribeTradeTicks
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.model.data import QuoteTick, TradeTick, BarType, Bar
from nautilus_trader.model.enums import BookType, PriceType
from nautilus_trader.model.identifiers import ClientId, InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity

if TYPE_CHECKING:
    from nautilus_trader.adapters.moomoo.providers import MoomooInstrumentProvider


class MoomooQuoteHandler:
    """Handler for real-time quote updates from Moomoo."""

    def __init__(self, client: MoomooDataClient):
        self._client = client

    def on_recv_rsp(self, rsp_str):
        """Handle quote response from Moomoo."""
        try:
            ret_code, data = rsp_str
            if ret_code != RET_OK:
                self._client._log.error(f"Quote handler error: {data}")
                return

            if data is None or (hasattr(data, 'empty') and data.empty):
                return

            # Process each row in the dataframe
            for _, row in data.iterrows():
                self._process_quote(row)

        except Exception as e:
            self._client._log.error(f"Error in quote handler: {e}")

    def _process_quote(self, row) -> None:
        """Process a single quote row into QuoteTick."""
        try:
            code = row.get('code', '')
            instrument_id = self._client._from_moomoo_code(code)

            # Get bid/ask prices and sizes
            bid_price = float(row.get('bid_price', 0) or 0)
            ask_price = float(row.get('ask_price', 0) or 0)
            bid_vol = float(row.get('bid_vol', 0) or 0)
            ask_vol = float(row.get('ask_vol', 0) or 0)

            if bid_price <= 0 or ask_price <= 0:
                return

            # Create timestamp
            ts_event = self._client._clock.timestamp_ns()

            quote_tick = QuoteTick(
                instrument_id=instrument_id,
                bid_price=Price.from_str(f"{bid_price:.4f}"),
                ask_price=Price.from_str(f"{ask_price:.4f}"),
                bid_size=Quantity.from_str(f"{int(bid_vol)}"),
                ask_size=Quantity.from_str(f"{int(ask_vol)}"),
                ts_event=ts_event,
                ts_init=ts_event,
            )

            self._client._handle_data(quote_tick)

        except Exception as e:
            self._client._log.error(f"Error processing quote: {e}")


class MoomooTickerHandler:
    """Handler for real-time ticker (trade) updates from Moomoo."""

    def __init__(self, client: MoomooDataClient):
        self._client = client
        self._trade_counter = 0

    def on_recv_rsp(self, rsp_str):
        """Handle ticker response from Moomoo."""
        try:
            ret_code, data = rsp_str
            if ret_code != RET_OK:
                self._client._log.error(f"Ticker handler error: {data}")
                return

            if data is None or (hasattr(data, 'empty') and data.empty):
                return

            for _, row in data.iterrows():
                self._process_trade(row)

        except Exception as e:
            self._client._log.error(f"Error in ticker handler: {e}")

    def _process_trade(self, row) -> None:
        """Process a single trade row into TradeTick."""
        try:
            code = row.get('code', '')
            instrument_id = self._client._from_moomoo_code(code)

            price = float(row.get('price', 0) or 0)
            volume = float(row.get('volume', 0) or 0)

            if price <= 0 or volume <= 0:
                return

            # Generate unique trade ID
            self._trade_counter += 1
            trade_id = TradeId(f"MOOMOO-{self._trade_counter}")

            ts_event = self._client._clock.timestamp_ns()

            trade_tick = TradeTick(
                instrument_id=instrument_id,
                price=Price.from_str(f"{price:.4f}"),
                size=Quantity.from_str(f"{int(volume)}"),
                aggressor_side=None,  # Moomoo doesn't provide this
                trade_id=trade_id,
                ts_event=ts_event,
                ts_init=ts_event,
            )

            self._client._handle_data(trade_tick)

        except Exception as e:
            self._client._log.error(f"Error processing trade: {e}")


class MoomooDataClient(LiveMarketDataClient):
    """
    Provides a data client for Moomoo using OpenD gateway.

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
    config : MoomooDataClientConfig
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
        config: MoomooDataClientConfig,
        name: str | None = None,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=ClientId(name or f"{MOOMOO_VENUE.value}-DATA"),
            venue=MOOMOO_VENUE,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            config=config,
        )

        self._config = config
        self._use_extended_hours = config.use_extended_hours
        self._markets = config.markets  # List of markets to subscribe to
        self._market = config.markets[0] if config.markets else "US"  # Default market for code conversion

        # Moomoo API context
        self._quote_ctx: OpenQuoteContext | None = None

        # Handlers
        self._quote_handler = MoomooQuoteHandler(self)
        self._ticker_handler = MoomooTickerHandler(self)

        # Subscription tracking
        self._subscribed_quotes: set[InstrumentId] = set()
        self._subscribed_trades: set[InstrumentId] = set()
        self._subscription_lock = asyncio.Lock()

        # Data polling task
        self._poll_task: asyncio.Task | None = None
        self._polling_interval: float = 1.0  # Poll every 1 second

    @property
    def instrument_provider(self) -> MoomooInstrumentProvider:
        return self._instrument_provider

    async def _connect(self) -> None:
        """Connect to Moomoo OpenD gateway."""
        self._log.info(
            f"Connecting to Moomoo OpenD gateway at "
            f"{self._config.gateway.host}:{self._config.gateway.port}..."
        )

        try:
            # Create quote context
            self._quote_ctx = OpenQuoteContext(
                host=self._config.gateway.host,
                port=self._config.gateway.port,
            )

            # Test connection
            ret, data = self._quote_ctx.get_global_state()
            if ret != RET_OK:
                raise ConnectionError(f"Failed to connect to Moomoo OpenD: {data}")

            self._log.info(f"Connected to Moomoo OpenD: {data}")

            # Start the data polling task
            self._poll_task = asyncio.create_task(self._poll_market_data())
            self._log.info("Started market data polling task")

            self._log.info("Moomoo data client connected successfully")

        except Exception as e:
            self._log.error(f"Connection failed: {e}")
            raise

    async def _poll_market_data(self) -> None:
        """Poll Moomoo for market data updates."""
        self._log.info("Market data polling loop started")
        while True:
            try:
                await asyncio.sleep(self._polling_interval)

                if self._quote_ctx is None:
                    break

                # Poll quotes for subscribed instruments
                if self._subscribed_quotes:
                    codes = [self._to_moomoo_code(inst_id) for inst_id in self._subscribed_quotes]
                    ret, data = self._quote_ctx.get_stock_quote(codes)
                    if ret == RET_OK and data is not None and not data.empty:
                        for _, row in data.iterrows():
                            self._quote_handler._process_quote(row)

                # Poll trades/tickers for subscribed instruments
                if self._subscribed_trades:
                    codes = [self._to_moomoo_code(inst_id) for inst_id in self._subscribed_trades]
                    ret, data = self._quote_ctx.get_rt_ticker(codes, num=10)
                    if ret == RET_OK and data is not None and not data.empty:
                        for _, row in data.iterrows():
                            self._ticker_handler._process_trade(row)

            except asyncio.CancelledError:
                self._log.info("Market data polling task cancelled")
                break
            except Exception as e:
                self._log.error(f"Error in market data polling: {e}")

    async def _disconnect(self) -> None:
        """Disconnect from Moomoo OpenD gateway."""
        self._log.info("Disconnecting from Moomoo OpenD gateway...")

        try:
            # Cancel polling task
            if self._poll_task is not None:
                self._poll_task.cancel()
                try:
                    await self._poll_task
                except asyncio.CancelledError:
                    pass
                self._poll_task = None

            # Unsubscribe from all instruments
            if self._quote_ctx:
                all_codes = []
                for inst_id in self._subscribed_quotes:
                    all_codes.append(self._to_moomoo_code(inst_id))
                for inst_id in self._subscribed_trades:
                    code = self._to_moomoo_code(inst_id)
                    if code not in all_codes:
                        all_codes.append(code)

                if all_codes:
                    self._quote_ctx.unsubscribe(
                        all_codes,
                        [SubType.QUOTE, SubType.TICKER, SubType.ORDER_BOOK]
                    )

                self._quote_ctx.close()
                self._quote_ctx = None

            self._subscribed_quotes.clear()
            self._subscribed_trades.clear()

            self._log.info("Moomoo data client disconnected")

        except Exception as e:
            self._log.error(f"Error during disconnect: {e}")

    def _to_moomoo_code(self, instrument_id: InstrumentId) -> str:
        """Convert NautilusTrader InstrumentId to Moomoo code format."""
        symbol = instrument_id.symbol.value
        if "." in symbol:
            return symbol
        return f"{self._market}.{symbol}"

    def _from_moomoo_code(self, code: str) -> InstrumentId:
        """Convert Moomoo code to NautilusTrader InstrumentId."""
        if "." in code:
            _, symbol = code.split(".", 1)
        else:
            symbol = code
        return InstrumentId.from_str(f"{symbol}.{MOOMOO_VENUE.value}")

    async def _subscribe_quote_ticks(self, command: SubscribeQuoteTicks) -> None:
        """Subscribe to quote ticks for an instrument."""
        instrument_id = command.instrument_id

        if self._quote_ctx is None:
            self._log.error("Not connected to Moomoo")
            return

        async with self._subscription_lock:
            if instrument_id in self._subscribed_quotes:
                self._log.warning(f"Already subscribed to quotes: {instrument_id}")
                return

            code = self._to_moomoo_code(instrument_id)
            ret, err = self._quote_ctx.subscribe(
                [code],
                [SubType.QUOTE],
                subscribe_push=True
            )

            if ret != RET_OK:
                self._log.warning(f"Failed to subscribe to quotes for {instrument_id}: {err}")
                # Don't raise - allow strategy to continue without real-time quotes
                # The strategy can still use polling for market data
                return

            self._subscribed_quotes.add(instrument_id)
            self._log.info(f"Subscribed to quote ticks for {instrument_id}")

            # Get initial snapshot
            await self._request_initial_quote(instrument_id, code)

    async def _request_initial_quote(self, instrument_id: InstrumentId, code: str) -> None:
        """Request initial quote snapshot."""
        try:
            ret, data = self._quote_ctx.get_stock_quote([code])
            if ret == RET_OK and data is not None and not data.empty:
                for _, row in data.iterrows():
                    self._quote_handler._process_quote(row)
        except Exception as e:
            self._log.warning(f"Failed to get initial quote for {instrument_id}: {e}")

    async def _subscribe_trade_ticks(self, command: SubscribeTradeTicks) -> None:
        """Subscribe to trade ticks for an instrument."""
        instrument_id = command.instrument_id

        if self._quote_ctx is None:
            self._log.error("Not connected to Moomoo")
            return

        async with self._subscription_lock:
            if instrument_id in self._subscribed_trades:
                self._log.warning(f"Already subscribed to trades: {instrument_id}")
                return

            code = self._to_moomoo_code(instrument_id)
            ret, err = self._quote_ctx.subscribe(
                [code],
                [SubType.TICKER],
                subscribe_push=True
            )

            if ret != RET_OK:
                self._log.error(f"Failed to subscribe to trades for {instrument_id}: {err}")
                raise RuntimeError(f"Subscription failed: {err}")

            self._subscribed_trades.add(instrument_id)
            self._log.info(f"Subscribed to trade ticks for {instrument_id}")

    async def _subscribe_bars(self, command: SubscribeBars) -> None:
        """Subscribe to bars for an instrument.

        Note: Moomoo doesn't support streaming bars, so we rely on polling
        and/or historical bar requests. This method logs the subscription
        but actual bar generation would need to be implemented via K-line polling.
        """
        bar_type = command.bar_type
        instrument_id = bar_type.instrument_id

        if self._quote_ctx is None:
            self._log.error("Not connected to Moomoo")
            return

        self._log.info(
            f"Bar subscription registered for {bar_type}. "
            f"Note: Moomoo uses polling for bar data, not push subscriptions."
        )

        # Add instrument to quote subscriptions for price tracking
        # Bars will be aggregated from quote data
        async with self._subscription_lock:
            if instrument_id not in self._subscribed_quotes:
                code = self._to_moomoo_code(instrument_id)
                ret, err = self._quote_ctx.subscribe(
                    [code],
                    [SubType.QUOTE],
                    subscribe_push=True
                )
                if ret == RET_OK:
                    self._subscribed_quotes.add(instrument_id)
                    self._log.info(f"Added quote subscription for bar aggregation: {instrument_id}")

    async def _subscribe_order_book_deltas(
        self,
        instrument_id: InstrumentId,
        book_type: BookType,
        depth: int | None = None,
    ) -> None:
        """Subscribe to order book deltas for an instrument."""
        if self._quote_ctx is None:
            self._log.error("Not connected to Moomoo")
            return

        async with self._subscription_lock:
            code = self._to_moomoo_code(instrument_id)
            ret, err = self._quote_ctx.subscribe(
                [code],
                [SubType.ORDER_BOOK],
                subscribe_push=True
            )

            if ret != RET_OK:
                self._log.error(f"Failed to subscribe to order book for {instrument_id}: {err}")
                raise RuntimeError(f"Subscription failed: {err}")

            self._log.info(f"Subscribed to order book for {instrument_id}")

    async def _unsubscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from quote ticks for an instrument."""
        if self._quote_ctx is None:
            return

        async with self._subscription_lock:
            if instrument_id not in self._subscribed_quotes:
                return

            code = self._to_moomoo_code(instrument_id)
            ret, _ = self._quote_ctx.unsubscribe([code], [SubType.QUOTE])

            if ret == RET_OK:
                self._subscribed_quotes.discard(instrument_id)
                self._log.info(f"Unsubscribed from quote ticks for {instrument_id}")

    async def _unsubscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from trade ticks for an instrument."""
        if self._quote_ctx is None:
            return

        async with self._subscription_lock:
            if instrument_id not in self._subscribed_trades:
                return

            code = self._to_moomoo_code(instrument_id)
            ret, _ = self._quote_ctx.unsubscribe([code], [SubType.TICKER])

            if ret == RET_OK:
                self._subscribed_trades.discard(instrument_id)
                self._log.info(f"Unsubscribed from trade ticks for {instrument_id}")

    async def _unsubscribe_order_book_deltas(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from order book deltas for an instrument."""
        if self._quote_ctx is None:
            return

        async with self._subscription_lock:
            code = self._to_moomoo_code(instrument_id)
            self._quote_ctx.unsubscribe([code], [SubType.ORDER_BOOK])
            self._log.info(f"Unsubscribed from order book for {instrument_id}")

    # Historical data methods - not fully implemented for Moomoo
    async def _request_quote_ticks(
        self,
        instrument_id: InstrumentId,
        limit: int,
        correlation_id: UUID4,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
    ) -> None:
        """Request historical quote ticks."""
        self._log.warning("Historical quote requests not implemented for Moomoo")

    async def _request_trade_ticks(
        self,
        instrument_id: InstrumentId,
        limit: int,
        correlation_id: UUID4,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
    ) -> None:
        """Request historical trade ticks."""
        self._log.warning("Historical trade requests not implemented for Moomoo")

    async def _request_bars(
        self,
        bar_type: BarType,
        limit: int,
        correlation_id: UUID4,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
    ) -> None:
        """Request historical bars."""
        self._log.warning("Historical bar requests not implemented for Moomoo")

    def get_subscription_status(self) -> dict:
        """Get current subscription status."""
        return {
            "connected": self._quote_ctx is not None,
            "quote_subscriptions": len(self._subscribed_quotes),
            "trade_subscriptions": len(self._subscribed_trades),
            "instruments": list(self._subscribed_quotes | self._subscribed_trades),
        }
