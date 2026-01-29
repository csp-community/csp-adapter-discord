"""Legacy adapter config - now use DiscordConfig from chatom.discord.

This module is deprecated. Use DiscordConfig from chatom.discord instead.
The DiscordAdapterConfig class is kept for backwards compatibility but
maps to chatom's DiscordConfig fields as closely as possible.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

__all__ = ("DiscordAdapterConfig",)


class DiscordAdapterConfig(BaseModel):
    """Legacy config class for Discord adapter.

    Deprecated: Use DiscordConfig from chatom.discord instead.

    This class is maintained for backwards compatibility. New code should use:
        from chatom.discord import DiscordConfig
        config = DiscordConfig(token="...", guild_id="...")
    """

    token: str = Field(description="The token for the Discord bot")
    intents: Optional[List[str]] = Field(
        default=None,
        description="The intents for the Discord bot (e.g., ['guilds', 'guild_messages'])",
    )

    @field_validator("token")
    def validate_token(cls, v):
        if Path(v).exists():
            v = Path(v).read_text().strip()
        if len(v) == 72:
            return v
        raise ValueError("Token must be valid or a file path")

    def to_discord_config(self):
        """Convert to chatom DiscordConfig.

        Returns:
            DiscordConfig: The equivalent chatom config.
        """
        from chatom.discord import DiscordConfig

        return DiscordConfig(
            bot_token=self.token,
            intents=self.intents,
        )
