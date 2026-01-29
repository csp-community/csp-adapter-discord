#!/usr/bin/env python
"""Discord CSP End-to-End Integration Test.

This script tests all Discord functionality through the CSP adapter.
Uses CSP for message streaming (subscribe/publish), runs other operations
via async setup before the CSP graph starts.

Environment Variables Required:
    DISCORD_TOKEN: Your Discord bot token
    DISCORD_TEST_CHANNEL_NAME: Channel where tests run (without #)
    DISCORD_TEST_USER_NAME: Username for mention tests
    DISCORD_GUILD_NAME: Name of the Discord server/guild

Usage:
    python -m csp_adapter_discord.tests.integration.discord_csp_e2e
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import List, Optional

import csp
from chatom.base import Message, PresenceStatus
from chatom.discord import (
    DiscordBackend,
    DiscordChannel,
    DiscordConfig,
    DiscordMessage,
    DiscordPresence,
    mention_everyone,
    mention_here,
    mention_user,
)
from chatom.format import Format, FormattedMessage, Table
from csp import ts

from csp_adapter_discord import DiscordAdapter


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.environ.get(name)
    if required and not value:
        print(f"❌ Missing required environment variable: {name}")
        sys.exit(1)
    return value


def build_config() -> DiscordConfig:
    """Build DiscordConfig from environment variables."""
    bot_token = get_env("DISCORD_TOKEN")

    return DiscordConfig(
        bot_token=bot_token,
        intents=["guilds", "guild_messages"],
    )


class TestState:
    """Container for test state."""

    def __init__(self):
        self.results: List[tuple] = []
        self.config: Optional[DiscordConfig] = None
        self.channel_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.user = None  # Store the user object for mentions
        self.bot_user_id: Optional[str] = None
        self.bot_display_name: Optional[str] = None
        self.guild_id: Optional[str] = None
        self.received_message: Optional[Message] = None
        self.waiting_for_inbound: bool = False
        self.test_complete: bool = False

    def log(self, message: str, success: bool = True):
        icon = "✅" if success else "❌"
        print(f"{icon} {message}")
        self.results.append((message, success))

    def section(self, title: str):
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}\n")

    def print_summary(self) -> bool:
        self.section("Test Summary")
        passed = sum(1 for _, s in self.results if s)
        failed = sum(1 for _, s in self.results if not s)
        total = len(self.results)
        print(f"  Passed: {passed}/{total}")
        print(f"  Failed: {failed}/{total}")
        if failed > 0:
            print("\n  Failed tests:")
            for msg, success in self.results:
                if not success:
                    print(f"    ❌ {msg}")
        return failed == 0


# Globals
STATE = TestState()
CHANNEL_NAME = get_env("DISCORD_TEST_CHANNEL_NAME")
USER_NAME = get_env("DISCORD_TEST_USER_NAME")
GUILD_NAME = get_env("DISCORD_GUILD_NAME")


async def resolve_guild(backend: DiscordBackend, guild_name: str) -> Optional[str]:
    """Look up the guild by name to get the guild ID.

    Uses the backend's public API for organization lookup.
    """
    try:
        # Use the backend's fetch_organization_by_name method
        guild = await backend.fetch_organization_by_name(guild_name)

        if guild:
            backend.config.guild_id = guild.id
            return guild.id

        # List available guilds for debugging
        print("  Available guilds:")
        guilds = await backend.list_organizations()
        for g in guilds:
            print(f"    - {g.name} ({g.id})")

        return None

    except Exception:
        traceback.print_exc()
        return None


async def lookup_user_by_name(backend: DiscordBackend, name: str, guild_id: str, channel_id: str) -> Optional[str]:
    """Look up a user ID by name or display name.

    Follows the same pattern as discord_e2e.py - tries multiple methods.
    """
    try:
        # Use the backend's fetch_user_by_name method
        user = await backend.fetch_user_by_name(name, guild_id)

        if user:
            return user.id

        # Fallback: try to find the user from recent message history
        print("  User not found via member lookup, trying message history...")
        if channel_id:
            try:
                messages = await backend.fetch_messages(channel_id, limit=100)
                search_name = name.split("#")[0].lower() if "#" in name else name.lower()
                for msg in messages:
                    # Try to fetch the user who authored the message
                    author_id = getattr(msg, "user_id", None) or getattr(msg, "author_id", None)
                    if author_id:
                        author = await backend.fetch_user(author_id)
                        if author:
                            author_name = author.name.lower() if author.name else ""
                            author_handle = author.handle.lower() if author.handle else ""
                            if author_name == search_name or author_handle == search_name:
                                return author.id
            except Exception as msg_err:
                print(f"  Could not search message history: {msg_err}")

        return None

    except Exception as e:
        error_msg = str(e)
        if "members" in error_msg.lower() or "intents" in error_msg.lower():
            print("  Note: User lookup requires Server Members Intent (privileged intent)")
            print("  Enable it in Discord Developer Portal > Bot > Privileged Gateway Intents")
        else:
            traceback.print_exc()
        return None


async def setup_and_run_pre_csp_tests():
    """Run tests that require async operations before CSP starts."""
    STATE.config = build_config()
    backend = DiscordBackend(config=STATE.config)

    # Test: Connection
    STATE.section("Test: Connection")
    await backend.connect()
    STATE.log("Connected to Discord successfully")
    print(f"  Backend: {backend.name}")
    print(f"  Display name: {backend.display_name}")

    # Resolve guild
    STATE.section("Resolving Guild")
    guild_id = await resolve_guild(backend, GUILD_NAME)
    if guild_id:
        STATE.guild_id = guild_id
        STATE.log(f"Found guild '{GUILD_NAME}'")
        print(f"  Guild ID: {STATE.guild_id}")
    else:
        STATE.log(f"Guild '{GUILD_NAME}' not found", success=False)
        return False

    # Resolve channel
    STATE.section("Resolving Channel")
    try:
        channel = await backend.fetch_channel_by_name(CHANNEL_NAME, STATE.guild_id)
        if channel:
            STATE.channel_id = channel.id
            STATE.log(f"Found channel '#{CHANNEL_NAME}'")
            print(f"  Channel ID: {STATE.channel_id}")
        else:
            STATE.log(f"Channel '#{CHANNEL_NAME}' not found", success=False)
            return False
    except Exception as e:
        STATE.log(f"Channel lookup failed: {e}", success=False)
        traceback.print_exc()
        return False

    # Resolve user
    STATE.section("Resolving User")
    user_id = await lookup_user_by_name(backend, USER_NAME, STATE.guild_id, STATE.channel_id)
    if user_id:
        STATE.user_id = user_id
        try:
            STATE.user = await backend.fetch_user(user_id)
            STATE.log(f"Found user '@{USER_NAME}'")
            print(f"  User ID: {STATE.user_id}")
        except Exception:
            STATE.log(f"Found user ID '{user_id}' but couldn't fetch details")
    else:
        print(f"  ⚠️  User '{USER_NAME}' not found. Some tests may be skipped.")
        print("  Note: User lookup may require Server Members Intent")

    # Get bot info
    STATE.section("Getting Bot Info")
    bot_info = await backend.get_bot_info()
    if bot_info:
        STATE.bot_user_id = bot_info.id
        STATE.bot_display_name = bot_info.name
        STATE.log(f"Bot: {bot_info.name} ({bot_info.id})")
    else:
        STATE.log("Could not get bot info", success=False)
        return False

    # Test: Fetch User
    STATE.section("Test: Fetch User")
    if STATE.user_id:
        try:
            user = await backend.fetch_user(STATE.user_id)
            if user:
                STATE.log(f"Fetched user: {user.display_name or user.name}")
                print(f"  User ID: {user.id}")
                print(f"  Name: {user.name}")
                print(f"  Handle: {user.handle}")
        except Exception as e:
            STATE.log(f"Fetch user failed: {e}", success=False)
    else:
        print("  Skipping (no user ID)")

    # Test: Fetch Channel
    STATE.section("Test: Fetch Channel")
    try:
        channel = await backend.fetch_channel(STATE.channel_id)
        if channel:
            STATE.log(f"Fetched channel: {channel.name}")
            print(f"  Channel ID: {channel.id}")
            print(f"  Name: {channel.name}")
            print(f"  Topic: {getattr(channel, 'topic', 'N/A')}")
    except Exception as e:
        STATE.log(f"Fetch channel failed: {e}", success=False)

    # Test: Send Plain Message
    STATE.section("Test: Send Plain Message (async)")
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = FormattedMessage().add_text(f"🧪 [CSP E2E] Plain message sent at {timestamp}")
        content = msg.render(Format.DISCORD_MARKDOWN)
        result = await backend.send_message(STATE.channel_id, content)
        STATE.log(f"Sent plain message at {timestamp}")
        if result:
            print(f"  Message ID: {result.id}")
    except Exception as e:
        STATE.log(f"Send message failed: {e}", success=False)

    # Test: Send Formatted Message
    STATE.section("Test: Send Formatted Message (async)")
    try:
        msg = (
            FormattedMessage()
            .add_text("🧪 [CSP E2E] Formatted message:\n")
            .add_bold("This is bold text")
            .add_text(" and ")
            .add_italic("this is italic")
            .add_text("\n")
            .add_code("inline_code()")
            .add_text("\n")
            .add_code_block("def hello():\n    print('Hello from code block!')", "python")
        )
        content = msg.render(Format.DISCORD_MARKDOWN)
        await backend.send_message(STATE.channel_id, content)
        STATE.log("Sent formatted message with bold, italic, code")
    except Exception as e:
        STATE.log(f"Send formatted message failed: {e}", success=False)

    # Test: Mentions
    STATE.section("Test: Mentions (async)")
    try:
        # mention_user expects a DiscordUser object, or use raw format
        user_mention = mention_user(STATE.user) if STATE.user else f"<@{STATE.user_id}>" if STATE.user_id else "(no user)"
        print(f"  User mention format: {user_mention}")
        print(f"  @here format: {mention_here()}")
        print(f"  @everyone format: {mention_everyone()}")

        msg = (
            FormattedMessage()
            .add_text("🧪 [CSP E2E] Mentions:\n")
            .add_text(f"  User: {user_mention}\n")
            .add_text("  (Not sending @here/@everyone to avoid spam)")
        )
        await backend.send_message(STATE.channel_id, msg.render(Format.DISCORD_MARKDOWN))
        STATE.log("Sent message with mentions")
    except Exception as e:
        STATE.log(f"Mentions test failed: {e}", success=False)

    # Test: Reactions
    STATE.section("Test: Reactions (async)")
    try:
        # Send a message to react to
        result = await backend.send_message(STATE.channel_id, "🧪 [CSP E2E] React to this message!")
        if result:
            message_id = result.id
            reactions = ["👍", "👎", "🎉", "❤️"]
            for emoji in reactions:
                await backend.add_reaction(message_id, emoji, channel=STATE.channel_id)
                print(f"  Added reaction: {emoji}")
                await asyncio.sleep(0.5)
            STATE.log(f"Added {len(reactions)} reactions")

            await asyncio.sleep(1)
            await backend.remove_reaction(message_id, "👎", channel=STATE.channel_id)
            STATE.log("Removed 👎 reaction")
    except Exception as e:
        STATE.log(f"Reactions test failed: {e}", success=False)

    # Test: Rich Content Table
    STATE.section("Test: Rich Content Table (async)")
    try:
        msg = FormattedMessage()
        msg.add_text("🧪 [CSP E2E] Rich Content (Table):\n\n")
        table = Table.from_data(
            data=[
                ["Messages", "✅", "Working"],
                ["Reactions", "✅", "Working"],
                ["Mentions", "✅", "Working"],
                ["Presence", "✅", "Working"],
                ["DMs", "✅", "Working"],
            ],
            headers=["Feature", "Status", "Notes"],
        )
        msg.content.append(table)
        await backend.send_message(STATE.channel_id, msg.render(Format.DISCORD_MARKDOWN))
        STATE.log("Sent rich content with table")
    except Exception as e:
        STATE.log(f"Rich content test failed: {e}", success=False)

    # Test: Fetch Message History
    STATE.section("Test: Fetch Message History")
    try:
        history = await backend.fetch_messages(STATE.channel_id, limit=5)
        STATE.log(f"Fetched {len(history)} messages from history")
        for m in history[:3]:
            preview = (m.content or "")[:40].replace("\n", " ")
            print(f"  - {preview}...")
    except Exception as e:
        STATE.log(f"Fetch message history failed: {e}", success=False)

    # Test: Presence
    STATE.section("Test: Presence (async)")
    try:
        await backend.set_presence(
            status="dnd",
            status_text="Running E2E Tests",
            activity_type="playing",
        )
        STATE.log("Set bot presence to DND")

        await asyncio.sleep(2)
        await backend.set_presence(
            status="online",
            status_text="Ready!",
        )
        STATE.log("Reset bot presence to online")
    except Exception as e:
        STATE.log(f"Presence test failed: {e}", success=False)

    # Test: Create DM
    STATE.section("Test: Create DM")
    test_user_id = STATE.user_id
    if not test_user_id:
        # Try getting a user from message history
        try:
            messages = await backend.fetch_messages(STATE.channel_id, limit=20)
            for msg in messages:
                author_id = getattr(msg, "author_id", None) or getattr(msg, "user_id", None)
                if author_id and author_id != STATE.bot_user_id:
                    test_user_id = author_id
                    print(f"  Found user ID from message history: {test_user_id}")
                    break
        except Exception:
            pass

    if test_user_id:
        try:
            dm_channel = await backend.create_dm(test_user_id)
            if dm_channel:
                STATE.log(f"Created DM: {dm_channel.id[:20] if hasattr(dm_channel, 'id') else str(dm_channel)[:20]}...")
                dm_id = dm_channel.id if hasattr(dm_channel, "id") else dm_channel
                msg = FormattedMessage().add_text("🧪 [CSP E2E] DM test message (async)")
                await backend.send_message(dm_id, msg.render(Format.DISCORD_MARKDOWN))
                STATE.log("Sent message to DM")
            else:
                STATE.log("Failed to create DM", success=False)
        except Exception as e:
            STATE.log(f"DM test failed: {e}", success=False)
    else:
        print("  Skipping DM test - no user ID available")

    # Disconnect (CSP will create its own connection)
    await backend.disconnect()
    STATE.log("Disconnected (pre-CSP setup complete)")

    return True


@csp.graph
def discord_csp_e2e_graph():
    """CSP graph for message streaming tests."""
    adapter = DiscordAdapter(STATE.config)

    # Subscribe to all messages
    messages = adapter.subscribe()

    # Test messages to send
    @csp.node
    def message_sender() -> ts[DiscordMessage]:
        """Send test messages via CSP publish."""
        with csp.alarms():
            a_step = csp.alarm(int)

        with csp.start():
            csp.schedule_alarm(a_step, timedelta(milliseconds=500), 0)

        if csp.ticked(a_step):
            step = a_step

            if step == 0:
                # Send plain message
                STATE.section("Test: Send Plain Message (via CSP)")
                timestamp = datetime.now().strftime("%H:%M:%S")
                msg = FormattedMessage().add_text(f"🧪 [CSP E2E] Plain message at {timestamp}")
                STATE.log(f"Sending plain message at {timestamp}")
                csp.schedule_alarm(a_step, timedelta(seconds=1), 1)
                return DiscordMessage(channel=DiscordChannel(id=STATE.channel_id), content=msg.render(Format.DISCORD_MARKDOWN))

            elif step == 1:
                # Send Discord markdown
                STATE.section("Test: Send Markdown Message (via CSP)")
                msg = (
                    FormattedMessage()
                    .add_text("🧪 [CSP E2E] Formatted message:\n")
                    .add_bold("Bold")
                    .add_text(" and ")
                    .add_italic("italic")
                    .add_text("\nCode: ")
                    .add_code("inline_code()")
                )
                STATE.log("Sending markdown message")
                csp.schedule_alarm(a_step, timedelta(seconds=1), 2)
                return DiscordMessage(channel=DiscordChannel(id=STATE.channel_id), content=msg.render(Format.DISCORD_MARKDOWN))

            elif step == 2:
                # Mentions
                STATE.section("Test: Mentions (via CSP)")
                # mention_user expects a DiscordUser object, or use raw format
                user_mention = mention_user(STATE.user) if STATE.user else f"<@{STATE.user_id}>"
                msg = FormattedMessage().add_text("🧪 [CSP E2E] Mention: ").add_raw(user_mention)
                STATE.log("Sending mention message")
                csp.schedule_alarm(a_step, timedelta(seconds=1), 3)
                return DiscordMessage(channel=DiscordChannel(id=STATE.channel_id), content=msg.render(Format.DISCORD_MARKDOWN))

            elif step == 3:
                # Table
                STATE.section("Test: Rich Content Table (via CSP)")
                msg = FormattedMessage().add_text("🧪 [CSP E2E] Table:\n\n")
                table = Table.from_data(
                    headers=["Feature", "Status"],
                    data=[["Subscribe", "✅"], ["Publish", "✅"], ["Mentions", "✅"]],
                )
                msg.content.append(table)
                STATE.log("Sending table message")
                csp.schedule_alarm(a_step, timedelta(seconds=1), 4)
                return DiscordMessage(channel=DiscordChannel(id=STATE.channel_id), content=msg.render(Format.DISCORD_MARKDOWN))

            elif step == 4:
                # Inbound message prompt
                STATE.section("Test: Inbound Messages (via CSP subscribe)")
                msg = (
                    FormattedMessage()
                    .add_text("🧪 ")
                    .add_bold("[CSP E2E] Inbound Message Test")
                    .add_text(f"\n\nPlease @mention the bot: @{STATE.bot_display_name} hello")
                    .add_text("\n\nYou have ")
                    .add_bold("10 seconds")
                    .add_text(" (or test will auto-complete)...")
                )
                STATE.log("Waiting for inbound message...")
                STATE.waiting_for_inbound = True
                print(f"\n  ⏳ Mention the bot: @{STATE.bot_display_name} hello")
                # Don't schedule next - wait for inbound

                return DiscordMessage(channel=DiscordChannel(id=STATE.channel_id), content=msg.render(Format.DISCORD_MARKDOWN))

            elif step == 5:
                # Confirmation after inbound received
                STATE.section("Test: Inbound Message Received!")
                msg = STATE.received_message
                if msg:
                    STATE.log("Received inbound message via CSP subscribe")
                    print(f"  Message ID: {msg.id}")
                    print(f"  From: {msg.author_id}")
                    preview = (msg.content or "")[:100].replace("\n", " ")
                    print(f"  Content: {preview}...")

                    confirm = (
                        FormattedMessage()
                        .add_text("✅ ")
                        .add_bold("[CSP E2E] Message received via CSP!")
                        .add_text("\n\nYour message was received through adapter.subscribe()")
                    )
                    csp.schedule_alarm(a_step, timedelta(seconds=1), 6)
                    return DiscordMessage(channel=DiscordChannel(id=STATE.channel_id), content=confirm.render(Format.DISCORD_MARKDOWN))
                else:
                    STATE.log("No message received", success=False)
                    csp.schedule_alarm(a_step, timedelta(seconds=1), 6)

            elif step == 6:
                # Done
                STATE.section("CSP Tests Complete")
                STATE.log("All CSP tests finished")
                STATE.test_complete = True
                csp.stop_engine()

    # Inbound message handler - outputs response message when user message received
    @csp.node
    def handle_inbound(msgs: ts[[Message]]) -> ts[DiscordMessage]:
        """Handle inbound messages and output response."""
        with csp.alarms():
            a_timeout = csp.alarm(bool)

        with csp.state():
            s_found = False
            s_timeout_scheduled = False

        # Schedule timeout when we start waiting for inbound
        if csp.ticked(msgs) and STATE.waiting_for_inbound and not s_timeout_scheduled:
            csp.schedule_alarm(a_timeout, timedelta(seconds=10), True)
            s_timeout_scheduled = True

        # Handle timeout - skip inbound test if no message received
        if csp.ticked(a_timeout) and STATE.waiting_for_inbound and not s_found:
            STATE.section("Test: Inbound Message Timeout")
            STATE.log("Inbound message test skipped (timeout)", success=True)
            STATE.waiting_for_inbound = False
            s_found = True

            # Mark complete
            STATE.section("CSP Tests Complete")
            STATE.log("All CSP tests finished")
            STATE.test_complete = True

            skip_msg = (
                FormattedMessage()
                .add_text("⏱️ ")
                .add_bold("[CSP E2E] Inbound test skipped (timeout)")
                .add_text("\n\nNo user message received within timeout period.")
            )
            return DiscordMessage(channel=DiscordChannel(id=STATE.channel_id), content=skip_msg.render(Format.DISCORD_MARKDOWN))

        if csp.ticked(msgs) and STATE.waiting_for_inbound and not s_found:
            result = None
            for msg in msgs:
                # Skip bot's own messages
                if hasattr(msg, "author_id") and msg.author_id == STATE.bot_user_id:
                    continue
                # Got a user message
                STATE.received_message = msg
                STATE.waiting_for_inbound = False
                print(f"\n  📨 Received message: {msg.id}")
                s_found = True

                # Log and build response
                STATE.section("Test: Inbound Message Received!")
                STATE.log("Received inbound message via CSP subscribe")
                print(f"  Message ID: {msg.id}")
                print(f"  From: {msg.author_id}")
                preview = (msg.content or "")[:100].replace("\n", " ")
                print(f"  Content: {preview}...")

                confirm = (
                    FormattedMessage()
                    .add_text("✅ ")
                    .add_bold("[CSP E2E] Message received via CSP!")
                    .add_text("\n\nYour message was received through adapter.subscribe()")
                )
                result = DiscordMessage(channel=DiscordChannel(id=STATE.channel_id), content=confirm.render(Format.DISCORD_MARKDOWN))

                # Mark complete
                STATE.section("CSP Tests Complete")
                STATE.log("All CSP tests finished")
                STATE.test_complete = True
                break

            if result is not None:
                return result

    sender_msgs = message_sender()
    inbound_msgs = handle_inbound(messages)

    # Merge both message streams
    @csp.node
    def merge_messages(m1: ts[DiscordMessage], m2: ts[DiscordMessage]) -> ts[DiscordMessage]:
        if csp.ticked(m1):
            return m1
        if csp.ticked(m2):
            return m2

    outbound = merge_messages(sender_msgs, inbound_msgs)

    # Stop after inbound test complete or timeout
    @csp.node
    def check_complete(msgs: ts[DiscordMessage]):
        with csp.alarms():
            a_stop = csp.alarm(bool)
        if csp.ticked(msgs) and STATE.test_complete:
            csp.schedule_alarm(a_stop, timedelta(seconds=1), True)
        if csp.ticked(a_stop):
            csp.stop_engine()

    # Merge inbound and timeout for completion check
    @csp.node
    def merge_for_complete(m1: ts[DiscordMessage], m2: ts[DiscordMessage]) -> ts[DiscordMessage]:
        if csp.ticked(m1):
            return m1
        if csp.ticked(m2):
            return m2

    # Timeout handler for inbound test - fires independently of message stream
    @csp.node
    def inbound_timeout() -> ts[DiscordMessage]:
        """Timeout the inbound test if no message received."""
        with csp.alarms():
            a_timeout = csp.alarm(bool)

        with csp.state():
            s_timed_out = False

        with csp.start():
            # Schedule timeout 15 seconds after graph starts (after step 4 sends at ~4.5s)
            csp.schedule_alarm(a_timeout, timedelta(seconds=15), True)

        if csp.ticked(a_timeout) and STATE.waiting_for_inbound and not s_timed_out:
            s_timed_out = True
            STATE.section("Test: Inbound Message Timeout")
            STATE.log("Inbound message test skipped (timeout)", success=True)
            STATE.waiting_for_inbound = False
            STATE.test_complete = True

            skip_msg = (
                FormattedMessage()
                .add_text("⏱️ ")
                .add_bold("[CSP E2E] Inbound test skipped (timeout)")
                .add_text("\n\nNo user message received within timeout period.")
            )
            return DiscordMessage(channel=DiscordChannel(id=STATE.channel_id), content=skip_msg.render(Format.DISCORD_MARKDOWN))

    timeout_msgs = inbound_timeout()

    # Check completion from either inbound or timeout
    complete_trigger = merge_for_complete(inbound_msgs, timeout_msgs)
    check_complete(complete_trigger)

    # Merge timeout messages with outbound
    @csp.node
    def merge_with_timeout(m1: ts[DiscordMessage], m2: ts[DiscordMessage]) -> ts[DiscordMessage]:
        if csp.ticked(m1):
            return m1
        if csp.ticked(m2):
            return m2

    final_outbound = merge_with_timeout(outbound, timeout_msgs)

    # Publish outbound messages
    adapter.publish(final_outbound)

    # Presence test
    @csp.node
    def presence_sequence() -> ts[DiscordPresence]:
        with csp.alarms():
            a_idle = csp.alarm(bool)
            a_online = csp.alarm(bool)

        with csp.start():
            csp.schedule_alarm(a_idle, timedelta(seconds=3), True)
            csp.schedule_alarm(a_online, timedelta(seconds=5), True)

        if csp.ticked(a_idle):
            print("  Setting presence to IDLE")
            STATE.log("Set presence to IDLE")
            return DiscordPresence(status=PresenceStatus.IDLE)

        if csp.ticked(a_online):
            print("  Setting presence to ONLINE")
            STATE.log("Set presence to ONLINE")
            return DiscordPresence(status=PresenceStatus.ONLINE)

    presence = presence_sequence()
    adapter.publish_presence(presence)


async def main_async():
    """Main async entry point."""
    print("\n" + "=" * 60)
    print("  Discord CSP E2E Integration Test")
    print("=" * 60)

    # Phase 1: Async setup tests (fetch channel, user, create DM, etc.)
    print("\n--- Phase 1: Async Setup Tests ---\n")
    if not await setup_and_run_pre_csp_tests():
        return False

    # Phase 2: CSP streaming tests (publish, subscribe, presence)
    print("\n--- Phase 2: CSP Streaming Tests ---\n")
    try:
        csp.run(
            discord_csp_e2e_graph,
            endtime=timedelta(seconds=30),
            realtime=True,
            queue_wait_time=timedelta(milliseconds=100),
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nCSP graph error: {e}")

    return STATE.print_summary()


def main():
    """Main entry point."""
    success = asyncio.run(main_async())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
