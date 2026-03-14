"""CSP adapter for Discord using chatom backend."""

__version__ = "0.1.2"

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
    # Adapter
    "DiscordAdapter",
    "DiscordAdapterManager",  # Legacy alias
    # Backend and config (from chatom)
    "DiscordBackend",
    "DiscordConfig",
    # Models (from chatom)
    "DiscordMessage",
    "DiscordMessageType",
    "DiscordMessageFlags",
    "DiscordUser",
    "DiscordChannel",
    "DiscordChannelType",
    "DiscordPresence",
    "DiscordActivity",
    "DiscordActivityType",
    # Utilities (from chatom)
    "mention_user",
    "mention_channel",
    "mention_role",
    "mention_everyone",
    "mention_here",
    # Testing
    "MockDiscordBackend",
    # Legacy
    "DiscordAdapterConfig",
)
