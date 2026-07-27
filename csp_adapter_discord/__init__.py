"""CSP adapter for Discord using chatom backend."""

__version__ = "0.2.2"

# Re-export from chatom.discord for convenience
from chatom.discord import (
    DiscordActivity,
    DiscordActivityType,
    DiscordBackend,
    DiscordChannel,
    DiscordChannelType,
    DiscordConfig,
    DiscordMessage,
    DiscordMessageFlags,
    DiscordMessageType,
    DiscordPresence,
    DiscordUser,
    MockDiscordBackend,
    mention_channel,
    mention_everyone,
    mention_here,
    mention_role,
    mention_user,
)

# Export the adapter
from .adapter import DiscordAdapter, DiscordAdapterManager

# Legacy imports for backwards compatibility
from .adapter_config import DiscordAdapterConfig

__all__ = (
    "DiscordActivity",
    "DiscordActivityType",
    "DiscordAdapter",
    "DiscordAdapterConfig",  # Legacy
    "DiscordAdapterManager",  # Legacy alias
    "DiscordBackend",
    "DiscordChannel",
    "DiscordChannelType",
    "DiscordConfig",
    "DiscordMessage",
    "DiscordMessageFlags",
    "DiscordMessageType",
    "DiscordPresence",
    "DiscordUser",
    "MockDiscordBackend",
    "mention_channel",
    "mention_everyone",
    "mention_here",
    "mention_role",
    "mention_user",
)
