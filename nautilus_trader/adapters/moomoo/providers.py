# -------------------------------------------------------------------------------------------------
#  Moomoo Instrument Provider for NautilusTrader
#  Provides instrument definitions from Moomoo API
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING

from moomoo import OpenQuoteContext, RET_OK, SecurityType, Market

from nautilus_trader.adapters.moomoo.common import MOOMOO_VENUE
from nautilus_trader.adapters.moomoo.config import MoomooGatewayConfig
from nautilus_trader.common.config import InstrumentProviderConfig
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.objects import Currency, Money, Price, Quantity

if TYPE_CHECKING:
    from nautilus_trader.common.component import LiveClock
    from nautilus_trader.cache.cache import Cache


class MoomooInstrumentProvider(InstrumentProvider):
    """
    Provides instrument definitions from Moomoo API.

    Parameters
    ----------
    gateway_config : MoomooGatewayConfig
        The gateway connection configuration.
    config : InstrumentProviderConfig
        The instrument provider configuration.
    clock : LiveClock
        The clock for timestamps.
    """

    def __init__(
        self,
        gateway_config: MoomooGatewayConfig,
        config: InstrumentProviderConfig,
        clock: LiveClock,
    ) -> None:
        super().__init__()

        self._gateway_config = gateway_config
        self._config = config
        self._clock = clock

        self._quote_ctx: OpenQuoteContext | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the instrument provider."""
        if self._initialized:
            return

        try:
            self._quote_ctx = OpenQuoteContext(
                host=self._gateway_config.host,
                port=self._gateway_config.port,
            )

            # Load initial instruments if specified
            if self._config.load_ids:
                for code in self._config.load_ids:
                    await self.load_async(code)

            self._initialized = True

        except Exception as e:
            raise RuntimeError(f"Failed to initialize instrument provider: {e}")

    async def load_async(self, moomoo_code: str) -> Equity | None:
        """
        Load an instrument by Moomoo code.

        Parameters
        ----------
        moomoo_code : str
            The Moomoo code (e.g., "US.AAPL").

        Returns
        -------
        Equity | None
            The loaded instrument or None if not found.
        """
        if self._quote_ctx is None:
            return None

        try:
            # Get stock basic info
            ret, data = self._quote_ctx.get_stock_basicinfo(
                market=Market.US,
                stock_type=SecurityType.STOCK,
                code_list=[moomoo_code],
            )

            if ret != RET_OK or data is None or data.empty:
                # Try with snapshot
                ret, data = self._quote_ctx.get_market_snapshot([moomoo_code])
                if ret != RET_OK or data is None or data.empty:
                    return None

            row = data.iloc[0]

            # Parse symbol from code
            if "." in moomoo_code:
                _, symbol = moomoo_code.split(".", 1)
            else:
                symbol = moomoo_code

            instrument_id = InstrumentId(
                symbol=Symbol(symbol),
                venue=MOOMOO_VENUE,
            )

            # Determine price precision from lot size
            lot_size = int(row.get('lot_size', 1) or 1)
            price_precision = 2  # Default for US stocks

            # Create Equity instrument
            ts_now = self._clock.timestamp_ns()

            instrument = Equity(
                instrument_id=instrument_id,
                raw_symbol=Symbol(moomoo_code),
                currency=Currency.from_str("USD"),
                price_precision=price_precision,
                price_increment=Price.from_str("0.01"),
                lot_size=Quantity.from_int(lot_size),
                ts_event=ts_now,
                ts_init=ts_now,
            )

            # Cache the instrument
            self.add(instrument)

            return instrument

        except Exception as e:
            self._log.error(f"Failed to load instrument {moomoo_code}: {e}")
            return None

    async def load_ids_async(
        self,
        instrument_ids: list[InstrumentId],
        filters: dict | None = None,
    ) -> None:
        """Load multiple instruments by ID."""
        for instrument_id in instrument_ids:
            symbol = instrument_id.symbol.value
            market = self._gateway_config.market
            moomoo_code = f"{market}.{symbol}"
            await self.load_async(moomoo_code)

    async def load_all_async(self, filters: dict | None = None) -> None:
        """Not supported - instruments loaded on demand."""
        pass

    def get_instrument_id_from_code(self, moomoo_code: str) -> InstrumentId:
        """Convert Moomoo code to InstrumentId."""
        if "." in moomoo_code:
            _, symbol = moomoo_code.split(".", 1)
        else:
            symbol = moomoo_code

        return InstrumentId(symbol=Symbol(symbol), venue=MOOMOO_VENUE)
