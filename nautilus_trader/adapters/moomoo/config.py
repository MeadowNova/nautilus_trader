# -------------------------------------------------------------------------------------------------
#  Configuration classes for Moomoo adapter
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from typing import Literal

from msgspec import field

from nautilus_trader.config import LiveDataClientConfig, LiveExecClientConfig, NautilusConfig


class MoomooGatewayConfig(NautilusConfig, frozen=True):
    """
    Configuration for Moomoo OpenD gateway connection.

    Parameters
    ----------
    host : str
        The OpenD gateway host address. Default is "127.0.0.1".
    port : int
        The OpenD gateway port. Default is 11111.
    trading_mode : Literal["paper", "live"]
        Trading mode - paper for simulation, live for real trading.
    security_firm : str
        The Moomoo security firm. Default is "FUTUSECURITIES".
    unlock_password : str | None
        Password for unlocking trade operations. Required for live trading only.
    """

    host: str = "127.0.0.1"
    port: int = 11111
    trading_mode: Literal["paper", "live"] = "paper"
    security_firm: str = "FUTUSECURITIES"
    unlock_password: str | None = None


class MoomooDataClientConfig(LiveDataClientConfig, frozen=True):
    """
    Configuration for MoomooDataClient.

    Parameters
    ----------
    gateway : MoomooGatewayConfig
        The gateway connection configuration.
    use_extended_hours : bool
        Whether to receive extended hours trading data. Default is False.
    subscription_quota : int
        Maximum number of subscriptions based on account tier. Default is 100.
    markets : list[str]
        List of markets to subscribe to. Default is ["US"].
    """

    gateway: MoomooGatewayConfig = MoomooGatewayConfig()
    use_extended_hours: bool = False
    subscription_quota: int = 100
    markets: list[str] = field(default_factory=lambda: ["US"])


class MoomooExecClientConfig(LiveExecClientConfig, frozen=True):
    """
    Configuration for MoomooExecClient.

    Parameters
    ----------
    gateway : MoomooGatewayConfig
        The gateway connection configuration.
    filter_trd_market : str
        Market to filter trading. Default is "US" for US stocks.
    max_orders_per_30s : int
        Maximum orders per 30 seconds (rate limit). Default is 15.
    enable_pre_trade_checks : bool
        Whether to perform pre-trade risk checks. Default is True.
    paper_account_id : str | None
        Specific paper trading account ID if multiple accounts exist.
    """

    gateway: MoomooGatewayConfig = MoomooGatewayConfig()
    filter_trd_market: str = "US"
    max_orders_per_30s: int = 15
    enable_pre_trade_checks: bool = True
    paper_account_id: str | None = None
