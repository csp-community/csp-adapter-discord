from pathlib import Path

from pydantic import BaseModel, Field, field_validator

__all__ = ("DiscordAdapterConfig",)


class DiscordAdapterConfig(BaseModel):
    """A config class that holds the required information to interact with Discord."""

    token: str = Field(description="The token for the Discord bot")

    @field_validator("token")
    def validate_token(cls, v):
        if Path(v).exists():
            v = Path(v).read_text().strip()
        if len(v) == 72:
            return v
        raise ValueError("Token must be valid or a file path")
