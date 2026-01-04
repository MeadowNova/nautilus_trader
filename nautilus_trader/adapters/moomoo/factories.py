# -------------------------------------------------------------------------------------------------
#  Moomoo Client Factories for NautilusTrader
#  Factory functions for creating data and execution clients
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from nautilus_trader.adapters.moomoo.common import MOOMOO_VENUE
from nautilus_trader.adapters.moomoo.config import (
    MoomooDataClientConfig,
    MoomooExecClientConfig,
)
from nautilus_trader.adapters.moomoo.data import MoomooDataClient
from nautilus_trader.adapters.moomoo.execution import MoomooExecClient
from nautilus_trader.adapters.moomoo.providers import MoomooInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.live.factories import LiveDataClientFactory, LiveExecClientFactory

if TYPE_CHECKING:
    from risk_management_framework import PositionRiskConfig, PortfolioRiskConfig


class MoomooLiveDataClientFactory(LiveDataClientFactory):
    """
    Factory for creating Moomoo data clients.

    Provides a standardized way to create and configure
    MoomooDataClient instances.
    """

    @staticmethod
    def create(
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: MoomooDataClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> MoomooDataClient:
        """
        Create a new MoomooDataClient.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The custom client ID.
        config : MoomooDataClientConfig
            The configuration for the client.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        MoomooDataClient
            The configured data client.
        """
        # Create instrument provider
        instrument_provider = MoomooInstrumentProvider(
            gateway_config=config.gateway,
            config=config.instrument_provider,
            clock=clock,
        )

        # Create data client
        client = MoomooDataClient(
            loop=loop,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            config=config,
            name=name,
        )

        return client


class MoomooLiveExecClientFactory(LiveExecClientFactory):
    """
    Factory for creating Moomoo execution clients.

    Provides a standardized way to create and configure
    MoomooExecClient instances with optional risk management.
    """

    @staticmethod
    def create(
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: MoomooExecClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> MoomooExecClient:
        """
        Create a new MoomooExecClient.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The custom client ID.
        config : MoomooExecClientConfig
            The configuration for the client.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        MoomooExecClient
            The configured execution client.
        """
        # Create instrument provider
        instrument_provider = MoomooInstrumentProvider(
            gateway_config=config.gateway,
            config=config.instrument_provider,
            clock=clock,
        )

        # Create execution client
        client = MoomooExecClient(
            loop=loop,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            config=config,
            name=name,
        )

        return client


def create_moomoo_clients(
    loop: asyncio.AbstractEventLoop,
    msgbus: MessageBus,
    cache: Cache,
    clock: LiveClock,
    data_config: MoomooDataClientConfig,
    exec_config: MoomooExecClientConfig,
) -> tuple[MoomooDataClient, MoomooExecClient]:
    """
    Create both data and execution clients.

    Convenience function to create both clients with shared configuration.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop.
    msgbus : MessageBus
        The message bus.
    cache : Cache
        The cache.
    clock : LiveClock
        The clock.
    data_config : MoomooDataClientConfig
        Data client configuration.
    exec_config : MoomooExecClientConfig
        Execution client configuration.

    Returns
    -------
    tuple[MoomooDataClient, MoomooExecClient]
        The data and execution clients.
    """
    data_client = MoomooLiveDataClientFactory.create(
        loop=loop,
        name="MOOMOO",
        config=data_config,
        msgbus=msgbus,
        cache=cache,
        clock=clock,
    )

    exec_client = MoomooLiveExecClientFactory.create(
        loop=loop,
        name="MOOMOO",
        config=exec_config,
        msgbus=msgbus,
        cache=cache,
        clock=clock,
    )

    return data_client, exec_client
