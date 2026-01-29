"""Tests for csp-adapter-discord."""


def test_import():
    """Test that all public exports can be imported."""
    from csp_adapter_discord import (
        DiscordAdapter,
        DiscordAdapterConfig,
        DiscordAdapterManager,
        DiscordBackend,
        DiscordConfig,
        DiscordMessage,
        DiscordPresence,
        mention_user,
    )

    assert DiscordAdapter is not None
    assert DiscordAdapterManager is DiscordAdapter  # Legacy alias
    assert DiscordBackend is not None
    assert DiscordConfig is not None
    assert DiscordMessage is not None
    assert DiscordPresence is not None
    assert DiscordAdapterConfig is not None
    assert mention_user is not None


def test_adapter_config_to_discord_config():
    """Test legacy DiscordAdapterConfig.to_discord_config()."""
    from csp_adapter_discord import DiscordAdapterConfig

    # Create legacy config (need a 72-char token)
    token = "x" * 72
    legacy_config = DiscordAdapterConfig(
        token=token,
        intents=["guilds", "guild_messages"],
    )

    # Convert to chatom config
    chatom_config = legacy_config.to_discord_config()

    assert chatom_config.bot_token.get_secret_value() == token
    assert chatom_config.intents == ["guilds", "guild_messages"]
