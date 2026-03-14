"""Discord CSP adapter using chatom backend.

This module provides a CSP adapter for Discord that wraps the chatom DiscordBackend.
"""

from typing import Optional, Set

import csp
from chatom.csp import BackendAdapter
from chatom.discord import DiscordBackend, DiscordConfig, DiscordMessage, DiscordPresence
from csp import ts

__all__ = ("DiscordAdapter", "DiscordAdapterManager")


class DiscordAdapter(BackendAdapter):
    """CSP adapter for Discord using the chatom DiscordBackend.

    This adapter wraps the chatom DiscordBackend and provides CSP
    graph/node methods for reading and writing messages.

    Attributes:
        backend: The underlying DiscordBackend.

    Example:
        >>> from csp_adapter_discord import DiscordAdapter, DiscordConfig
        >>>
        >>> config = DiscordConfig(bot_token="your-bot-token")
        >>> adapter = DiscordAdapter(config=config)
        >>>
        >>> @csp.graph
        ... def my_graph():
        ...     messages = adapter.subscribe()
        ...     # Process messages
        ...     responses = process(messages)
        ...     adapter.publish(responses)
        >>>
        >>> csp.run(my_graph, starttime=datetime.now(), endtime=timedelta(hours=1))
    """

    def __init__(self, config: DiscordConfig):
        """Initialize the Discord adapter.

        Args:
            config: Discord configuration.
        """
        backend = DiscordBackend(config=config)
        super().__init__(backend)

    # NOTE: Cannot use @csp.graph decorator, https://github.com/Point72/csp/issues/183
    def subscribe(
        self,
        channels: Optional[Set[str]] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> ts[[DiscordMessage]]:
        """Subscribe to messages from Discord.

        Args:
            channels: Optional set of channel IDs or names to filter.
                Names will be resolved to IDs at connection time.
            skip_own: If True, skip messages from the bot itself.
            skip_history: If True, skip messages before stream started.

        Returns:
            Time series of DiscordMessage lists.

        Example:
            >>> @csp.graph
            ... def my_graph():
            ...     # Subscribe to specific channels
            ...     messages = adapter.subscribe(channels={"general", "bot-commands"})
            ...     csp.print("Received", messages)
        """
        # Use the base class subscribe which returns ts[[Message]]
        # The messages will be DiscordMessage instances
        return super().subscribe(
            channels=channels,
            skip_own=skip_own,
            skip_history=skip_history,
        )

    # NOTE: Cannot use @csp.graph decorator, https://github.com/Point72/csp/issues/183
    def publish(self, msg: ts[DiscordMessage]):
        """Publish messages to Discord.

        Args:
            msg: Time series of DiscordMessage to send.

        Example:
            >>> @csp.graph
            ... def my_graph():
            ...     response = csp.const(DiscordMessage(
            ...         channel_id="1234567890",
            ...         content="Hello, World!",
            ...     ))
            ...     adapter.publish(response)
        """
        super().publish(msg=msg)

    @csp.node
    def _extract_presence_status(self, p: ts[DiscordPresence]) -> ts[str]:
        """Extract status string from DiscordPresence."""
        if csp.ticked(p):
            return p.status.value if hasattr(p.status, "value") else str(p.status)

    # NOTE: Cannot use @csp.graph decorator, https://github.com/Point72/csp/issues/183
    def publish_presence(self, presence: ts[DiscordPresence], timeout: float = 5.0):
        """Publish presence/activity status updates.

        Args:
            presence: Time series of DiscordPresence status.
            timeout: Timeout for presence API calls.

        Example:
            >>> @csp.graph
            ... def my_graph():
            ...     presence = csp.const(DiscordPresence(
            ...         status=PresenceStatus.ONLINE,
            ...     ))
            ...     adapter.publish_presence(presence)
        """
        # Extract the status string from DiscordPresence
        status_str = self._extract_presence_status(presence)
        super().publish_presence(presence=status_str, timeout=timeout)


# Legacy alias for backwards compatibility
DiscordAdapterManager = DiscordAdapter
