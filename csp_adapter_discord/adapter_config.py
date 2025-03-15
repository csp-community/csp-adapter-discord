from pathlib import Path

from discord import Intents
from pydantic import BaseModel, Field, field_validator

__all__ = ("DiscordAdapterConfig",)


def _get_default_intents_plus_read():
    ret = Intents.default()
    ret.message_content = True
    return ret.value


class DiscordAdapterConfig(BaseModel):
    """A config class that holds the required information to interact with Discord."""

    token: str = Field(description="The token for the Discord bot")
    intents: int = Field(default_factory=_get_default_intents_plus_read, description="The intents for the Discord bot")

    @field_validator("token")
    def validate_token(cls, v):
        if Path(v).exists():
            v = Path(v).read_text().strip()
        if len(v) == 72:
            return v
        raise ValueError("Token must be valid or a file path")

    @field_validator("intents")
    def validate_intents(cls, v):
        if isinstance(v, Intents):
            return v.value
        return v
