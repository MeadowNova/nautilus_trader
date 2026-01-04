# -------------------------------------------------------------------------------------------------
#  Common constants and utilities for Moomoo adapter
# -------------------------------------------------------------------------------------------------

from enum import Enum

from nautilus_trader.model.identifiers import Venue


# Moomoo venue identifier
MOOMOO_VENUE = Venue("MOOMOO")


class MoomooMarket(str, Enum):
    """Moomoo market identifiers."""
    US = "US"          # US stocks
    HK = "HK"          # Hong Kong stocks
    SH = "SH"          # Shanghai stocks
    SZ = "SZ"          # Shenzhen stocks
    SG = "SG"          # Singapore stocks
    JP = "JP"          # Japan stocks


class MoomooTradingMode(str, Enum):
    """Trading mode for Moomoo."""
    PAPER = "paper"
    LIVE = "live"


class MoomooOrderType(str, Enum):
    """Moomoo order types."""
    NORMAL = "NORMAL"                    # Limit order (default)
    MARKET = "MARKET"                    # Market order
    LIMIT_IF_TOUCHED = "LIMIT_IF_TOUCHED"  # LIT order
    MARKET_IF_TOUCHED = "MARKET_IF_TOUCHED"  # MIT order
    STOP = "STOP"                        # Stop order
    STOP_LIMIT = "STOP_LIMIT"            # Stop limit order


class MoomooSecurityFirm(str, Enum):
    """Moomoo security firms."""
    FUTUSECURITIES = "FUTUSECURITIES"
    FUTUNNU = "FUTUNNU"
    FUTUINC = "FUTUINC"
    FUTUAU = "FUTUAU"
    FUTUSG = "FUTUSG"


# Rate limiting constants
ORDER_RATE_LIMIT = 15  # orders per 30 seconds
QUOTE_SUBSCRIPTION_LIMIT = 100  # per account tier


def moomoo_symbol_to_instrument_id(moomoo_code: str) -> str:
    """
    Convert Moomoo code format to NautilusTrader InstrumentId format.

    Example: "US.AAPL" -> "AAPL.MOOMOO"
    """
    parts = moomoo_code.split(".")
    if len(parts) == 2:
        market, symbol = parts
        return f"{symbol}.{MOOMOO_VENUE.value}"
    return f"{moomoo_code}.{MOOMOO_VENUE.value}"


def instrument_id_to_moomoo_symbol(instrument_id: str, market: str = "US") -> str:
    """
    Convert NautilusTrader InstrumentId format to Moomoo code format.

    Example: "AAPL.MOOMOO" -> "US.AAPL"
    """
    parts = instrument_id.split(".")
    if len(parts) >= 1:
        symbol = parts[0]
        return f"{market}.{symbol}"
    return f"{market}.{instrument_id}"
