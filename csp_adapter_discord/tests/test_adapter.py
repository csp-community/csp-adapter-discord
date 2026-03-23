"""Tests for csp-adapter-discord."""

import asyncio
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import csp
import pytest
from pydantic import ValidationError

from csp_adapter_discord import (
    DiscordActivity,
    DiscordActivityType,
    DiscordAdapter,
    DiscordAdapterConfig,
    DiscordAdapterManager,
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

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------


class TestImports:
    def test_all_exports(self):
        """All __all__ exports are importable and non-None."""
        assert DiscordAdapter is not None
        assert DiscordAdapterManager is DiscordAdapter
        assert DiscordBackend is not None
        assert DiscordConfig is not None
        assert DiscordMessage is not None
        assert DiscordMessageType is not None
        assert DiscordMessageFlags is not None
        assert DiscordUser is not None
        assert DiscordChannel is not None
        assert DiscordChannelType is not None
        assert DiscordPresence is not None
        assert DiscordActivity is not None
        assert DiscordActivityType is not None
        assert MockDiscordBackend is not None
        assert DiscordAdapterConfig is not None
        assert mention_user is not None
        assert mention_channel is not None
        assert mention_role is not None
        assert mention_everyone is not None
        assert mention_here is not None

    def test_version(self):
        import csp_adapter_discord

        assert hasattr(csp_adapter_discord, "__version__")
        assert isinstance(csp_adapter_discord.__version__, str)


# ---------------------------------------------------------------------------
# Legacy DiscordAdapterConfig
# ---------------------------------------------------------------------------


class TestDiscordAdapterConfig:
    def test_valid_token(self):
        token = "x" * 72
        config = DiscordAdapterConfig(token=token)
        assert config.token == token

    def test_invalid_token_too_short(self):
        with pytest.raises(ValidationError):
            DiscordAdapterConfig(token="tooshort")

    def test_invalid_token_too_long(self):
        with pytest.raises(ValidationError):
            DiscordAdapterConfig(token="x" * 100)

    def test_token_from_file(self):
        token = "A" * 72
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(token)
            f.flush()
            config = DiscordAdapterConfig(token=f.name)
        assert config.token == token

    def test_default_intents_none(self):
        config = DiscordAdapterConfig(token="x" * 72)
        assert config.intents is None

    def test_custom_intents(self):
        config = DiscordAdapterConfig(
            token="x" * 72,
            intents=["guilds", "guild_messages"],
        )
        assert config.intents == ["guilds", "guild_messages"]

    def test_to_discord_config(self):
        token = "x" * 72
        legacy = DiscordAdapterConfig(token=token, intents=["guilds", "guild_messages"])
        chatom_config = legacy.to_discord_config()
        resolved = chatom_config.bot_token if isinstance(chatom_config.bot_token, str) else chatom_config.bot_token.get_secret_value()
        assert resolved == token
        assert chatom_config.intents == ["guilds", "guild_messages"]

    def test_to_discord_config_no_intents(self):
        """When intents is None, to_discord_config passes None which DiscordConfig rejects."""
        token = "x" * 72
        legacy = DiscordAdapterConfig(token=token)
        # DiscordConfig requires intents to be a list, so None raises
        with pytest.raises(ValidationError):
            legacy.to_discord_config()


# ---------------------------------------------------------------------------
# Discord models (chatom re-exports)
# ---------------------------------------------------------------------------


class TestDiscordMessage:
    def test_create_basic(self):
        msg = DiscordMessage(content="Hello!", channel=DiscordChannel(id="456", name="general"))
        assert msg.content == "Hello!"
        assert msg.channel_id == "456"
        assert msg.channel_name == "general"

    def test_create_with_author(self):
        msg = DiscordMessage(
            channel_id="456",
            content="Hello!",
            author=DiscordUser(id="123", name="TestUser"),
        )
        assert msg.author.id == "123"
        assert msg.author.name == "TestUser"

    def test_text_alias(self):
        msg = DiscordMessage(text="Hello via alias!")
        assert msg.content == "Hello via alias!"

    def test_default_values(self):
        msg = DiscordMessage()
        assert msg.content == ""
        assert msg.is_edited is False
        assert msg.is_pinned is False
        assert msg.is_bot is False

    def test_message_type(self):
        assert DiscordMessageType is not None
        assert hasattr(DiscordMessageType, "DEFAULT")

    def test_message_flags(self):
        assert DiscordMessageFlags is not None


class TestDiscordUser:
    def test_create_basic(self):
        user = DiscordUser(id="123", name="TestUser")
        assert user.id == "123"
        assert user.name == "TestUser"

    def test_with_handle(self):
        user = DiscordUser(id="123", name="TestUser", handle="testuser")
        assert user.handle == "testuser"

    def test_bot_user(self):
        user = DiscordUser(id="999", name="Bot", is_bot=True)
        assert user.is_bot is True

    def test_discriminator(self):
        user = DiscordUser(id="123", name="TestUser", discriminator="1234")
        assert user.discriminator == "1234"


class TestDiscordChannel:
    def test_create_basic(self):
        channel = DiscordChannel(id="456", name="general")
        assert channel.id == "456"
        assert channel.name == "general"

    def test_channel_type(self):
        assert DiscordChannelType is not None

    def test_with_topic(self):
        channel = DiscordChannel(id="456", name="general", topic="Main channel")
        assert channel.topic == "Main channel"


class TestDiscordPresence:
    def test_create_basic(self):
        presence = DiscordPresence(status="online")
        assert str(presence.status.value) == "online"

    def test_with_status_text(self):
        presence = DiscordPresence(status="dnd", status_text="Busy")
        assert presence.status_text == "Busy"

    def test_activity_types(self):
        assert DiscordActivityType is not None
        assert DiscordActivity is not None


# ---------------------------------------------------------------------------
# Mentions (chatom re-exports)
# ---------------------------------------------------------------------------


class TestMentions:
    def test_mention_user(self):
        user = DiscordUser(id="123", name="TestUser")
        assert mention_user(user) == "<@123>"

    def test_mention_channel(self):
        channel = DiscordChannel(id="456", name="general")
        assert mention_channel(channel) == "<#456>"

    def test_mention_role(self):
        assert mention_role("999") == "<@&999>"

    def test_mention_everyone(self):
        assert mention_everyone() == "@everyone"

    def test_mention_here(self):
        assert mention_here() == "@here"


# ---------------------------------------------------------------------------
# MockDiscordBackend
# ---------------------------------------------------------------------------


class TestMockBackend:
    def _make_mock(self):
        config = DiscordConfig(bot_token="fake_token_for_testing")
        mock = MockDiscordBackend(config=config)
        return mock

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        mock = self._make_mock()
        await mock.connect()
        await mock.disconnect()

    def test_add_mock_user(self):
        mock = self._make_mock()
        user = mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        assert user.id == "123"
        assert user.name == "TestUser"
        assert user.handle == "testuser"

    def test_add_mock_channel(self):
        mock = self._make_mock()
        channel = mock.add_mock_channel(id="456", name="general", channel_type="text")
        assert channel.id == "456"
        assert channel.name == "general"

    def test_add_mock_message(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        mock.add_mock_channel(id="456", name="general")
        msg_id = mock.add_mock_message(channel_id="456", user_id="123", content="Hello!")
        assert msg_id is not None

    @pytest.mark.asyncio
    async def test_fetch_user(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        await mock.connect()
        user = await mock.fetch_user(id="123")
        assert user is not None
        assert user.name == "TestUser"

    @pytest.mark.asyncio
    async def test_fetch_user_not_found(self):
        mock = self._make_mock()
        await mock.connect()
        user = await mock.fetch_user(id="nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_fetch_channel(self):
        mock = self._make_mock()
        mock.add_mock_channel(id="456", name="general")
        await mock.connect()
        channel = await mock.fetch_channel(id="456")
        assert channel is not None
        assert channel.name == "general"

    @pytest.mark.asyncio
    async def test_fetch_channel_not_found(self):
        mock = self._make_mock()
        await mock.connect()
        channel = await mock.fetch_channel(id="nonexistent")
        assert channel is None

    @pytest.mark.asyncio
    async def test_fetch_messages(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        mock.add_mock_channel(id="456", name="general")
        mock.add_mock_message(channel_id="456", user_id="123", content="Hello!")
        mock.add_mock_message(channel_id="456", user_id="123", content="World!")
        await mock.connect()
        messages = await mock.fetch_messages(channel="456", limit=10)
        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_send_message(self):
        mock = self._make_mock()
        mock.add_mock_channel(id="456", name="general")
        await mock.connect()
        sent = await mock.send_message(channel="456", content="Sent Message")
        assert sent.content == "Sent Message"
        assert len(mock.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_edit_message(self):
        mock = self._make_mock()
        mock.add_mock_channel(id="456", name="general")
        await mock.connect()
        sent = await mock.send_message(channel="456", content="Original")
        edited = await mock.edit_message(message=sent.id, content="Edited", channel="456")
        assert edited.content == "Edited"
        assert len(mock.edited_messages) == 1

    @pytest.mark.asyncio
    async def test_delete_message(self):
        mock = self._make_mock()
        mock.add_mock_channel(id="456", name="general")
        await mock.connect()
        sent = await mock.send_message(channel="456", content="To Delete")
        await mock.delete_message(message=sent.id, channel="456")
        assert len(mock.deleted_messages) == 1

    @pytest.mark.asyncio
    async def test_add_reaction(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        mock.add_mock_channel(id="456", name="general")
        msg_id = mock.add_mock_message(channel_id="456", user_id="123", content="React to me")
        await mock.connect()
        await mock.add_reaction(message=msg_id, emoji="thumbsup", channel="456")
        reactions = mock.get_reactions()
        assert len(reactions) == 1
        assert reactions[0]["emoji"] == "thumbsup"

    @pytest.mark.asyncio
    async def test_remove_reaction(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        mock.add_mock_channel(id="456", name="general")
        msg_id = mock.add_mock_message(channel_id="456", user_id="123", content="React to me")
        await mock.connect()
        await mock.add_reaction(message=msg_id, emoji="thumbsup", channel="456")
        await mock.remove_reaction(message=msg_id, emoji="thumbsup", channel="456")
        reactions = mock.get_reactions()
        assert len(reactions) == 2
        assert reactions[1]["action"] == "remove"

    @pytest.mark.asyncio
    async def test_set_and_get_presence(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        await mock.connect()
        await mock.set_presence(status="online")
        updates = mock.get_presence_updates()
        assert len(updates) == 1
        assert updates[0]["status"] == "online"

    @pytest.mark.asyncio
    async def test_set_mock_presence(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        presence = mock.set_mock_presence(user_id="123", status="online")
        assert presence is not None
        await mock.connect()
        fetched = await mock.get_presence(user="123")
        assert fetched is not None

    @pytest.mark.asyncio
    async def test_create_dm(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        await mock.connect()
        dm_id = await mock.create_dm(users=["123"])
        assert dm_id is not None
        assert len(mock.created_dms) == 1

    def test_clear(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        mock.add_mock_channel(id="456", name="general")
        mock.add_mock_message(channel_id="456", user_id="123", content="Hello!")

        async def _send_and_clear():
            await mock.connect()
            await mock.send_message(channel="456", content="msg")
            assert len(mock.sent_messages) == 1
            mock.clear()
            assert len(mock.sent_messages) == 0

        asyncio.run(_send_and_clear())

    @pytest.mark.asyncio
    async def test_forward_message(self):
        mock = self._make_mock()
        mock.add_mock_user(id="123", name="TestUser", handle="testuser")
        mock.add_mock_channel(id="456", name="general")
        mock.add_mock_channel(id="789", name="other")
        mock.add_mock_message(channel_id="456", user_id="123", content="Forward me")
        await mock.connect()
        messages = await mock.fetch_messages(channel="456", limit=1)
        forwarded = await mock.forward_message(message=messages[0], to_channel="789")
        assert forwarded is not None


# ---------------------------------------------------------------------------
# DiscordAdapter
# ---------------------------------------------------------------------------


class TestDiscordAdapter:
    def test_init(self):
        """DiscordAdapter.__init__ creates a DiscordBackend and passes it to super."""
        config = DiscordConfig(bot_token="fake_token_for_testing")
        with patch("csp_adapter_discord.adapter.DiscordBackend") as mock_backend_cls:
            mock_backend = MagicMock()
            mock_backend_cls.return_value = mock_backend
            adapter = DiscordAdapter(config=config)
            mock_backend_cls.assert_called_once_with(config=config)
            assert adapter.backend is mock_backend

    def test_legacy_alias(self):
        assert DiscordAdapterManager is DiscordAdapter

    def test_subscribe_calls_super(self):
        """subscribe delegates to BackendAdapter.subscribe with correct args."""
        config = DiscordConfig(bot_token="fake_token_for_testing")
        with patch("csp_adapter_discord.adapter.DiscordBackend"):
            adapter = DiscordAdapter(config=config)
            with patch.object(type(adapter).__bases__[0], "subscribe", return_value="mock_ts") as mock_sub:
                result = adapter.subscribe(channels={"general"}, skip_own=False, skip_history=False)
                mock_sub.assert_called_once_with(channels={"general"}, skip_own=False, skip_history=False)
                assert result == "mock_ts"

    def test_publish_calls_super(self):
        """publish delegates to BackendAdapter.publish."""
        config = DiscordConfig(bot_token="fake_token_for_testing")
        with patch("csp_adapter_discord.adapter.DiscordBackend"):
            adapter = DiscordAdapter(config=config)
            mock_msg = MagicMock()
            with patch.object(type(adapter).__bases__[0], "publish") as mock_pub:
                adapter.publish(mock_msg)
                mock_pub.assert_called_once_with(msg=mock_msg)

    def test_publish_presence_calls_super(self):
        """publish_presence extracts status string and delegates."""
        config = DiscordConfig(bot_token="fake_token_for_testing")
        with patch("csp_adapter_discord.adapter.DiscordBackend"):
            adapter = DiscordAdapter(config=config)
            mock_presence = MagicMock()
            # _extract_presence_status is a csp.node; we mock it
            with patch.object(adapter, "_extract_presence_status", return_value="status_ts") as mock_extract:
                with patch.object(type(adapter).__bases__[0], "publish_presence") as mock_pub_pres:
                    adapter.publish_presence(mock_presence, timeout=10.0)
                    mock_extract.assert_called_once_with(mock_presence)
                    mock_pub_pres.assert_called_once_with(presence="status_ts", timeout=10.0)

    def test_extract_presence_status_with_enum(self):
        """_extract_presence_status extracts status.value from DiscordPresence."""
        config = DiscordConfig(bot_token="fake_token_for_testing")
        with patch("csp_adapter_discord.adapter.DiscordBackend"):
            adapter = DiscordAdapter(config=config)

        @csp.graph
        def g() -> csp.Outputs(result=csp.ts[str]):
            presence = csp.const(DiscordPresence(status="online"))
            result = adapter._extract_presence_status(presence)
            csp.output(result=result)

        out = csp.run(g, starttime=datetime.now(), endtime=timedelta(seconds=1))
        assert len(out["result"]) == 1
        assert out["result"][0][1] == "online"

    def test_extract_presence_status_with_string(self):
        """_extract_presence_status handles a raw string status."""
        config = DiscordConfig(bot_token="fake_token_for_testing")
        with patch("csp_adapter_discord.adapter.DiscordBackend"):
            adapter = DiscordAdapter(config=config)

        @csp.graph
        def g() -> csp.Outputs(result=csp.ts[str]):
            presence = csp.const(DiscordPresence(status="idle"))
            result = adapter._extract_presence_status(presence)
            csp.output(result=result)

        out = csp.run(g, starttime=datetime.now(), endtime=timedelta(seconds=1))
        assert len(out["result"]) == 1
        assert out["result"][0][1] == "idle"

    def test_extract_presence_status_dnd(self):
        config = DiscordConfig(bot_token="fake_token_for_testing")
        with patch("csp_adapter_discord.adapter.DiscordBackend"):
            adapter = DiscordAdapter(config=config)

        @csp.graph
        def g() -> csp.Outputs(result=csp.ts[str]):
            presence = csp.const(DiscordPresence(status="dnd"))
            result = adapter._extract_presence_status(presence)
            csp.output(result=result)

        out = csp.run(g, starttime=datetime.now(), endtime=timedelta(seconds=1))
        assert out["result"][0][1] == "dnd"
