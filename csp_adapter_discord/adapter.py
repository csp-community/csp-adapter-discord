import threading
from asyncio import sleep as asleep
from io import StringIO
from logging import getLogger
from queue import Queue
from threading import Thread
from time import sleep
from typing import Dict, TypeVar, Union

import csp
from csp.impl.adaptermanager import AdapterManagerImpl
from csp.impl.outputadapter import OutputAdapter
from csp.impl.pushadapter import PushInputAdapter
from csp.impl.types.tstype import ts
from csp.impl.wiring import py_output_adapter_def, py_push_adapter_def
from discord import Client, DMChannel, File, GroupChannel, Intents, TextChannel, User
from discord.utils import get

from .adapter_config import DiscordAdapterConfig
from .message import DiscordMessage

T = TypeVar("T")
Channel = Union[DMChannel, TextChannel, GroupChannel]
log = getLogger(__file__)


__all__ = ("DiscordAdapterManager",)


class DiscordAdapterManager(AdapterManagerImpl):
    _discord_client: Client
    _token: str

    def __init__(self, config: DiscordAdapterConfig):
        self._discord_client = Client(intents=Intents(config.intents))
        self._token = config.token

        # down stream edges
        self._subscribers = []
        self._publishers = []

        # message queues
        self._inqueue: Queue[DiscordMessage] = Queue()
        self._outqueue: Queue[DiscordMessage] = Queue()

        # handler thread
        self._running: bool = False
        self._thread: Thread = None

        # lookups for mentions and redirection
        self._channel_id_to_channel: Dict[str, Channel] = {}
        self._channel_name_to_channel: Dict[str, Channel] = {}
        self._user_id_to_user: Dict[str, User] = {}
        self._user_name_to_user: Dict[str, User] = {}

    def subscribe(self):
        return _discord_input_adapter(self, push_mode=csp.PushMode.NON_COLLAPSING)

    def publish(self, msg: ts[DiscordMessage]):
        return _discord_output_adapter(self, msg)

    def _create(self, engine, memo):
        # We'll avoid having a second class and make our AdapterManager and AdapterManagerImpl the same
        super().__init__(engine)
        return self

    def start(self, starttime, endtime):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._running:
            self._running = False
            self._discord_client.close()
            self._thread.join()

    def register_subscriber(self, adapter):
        if adapter not in self._subscribers:
            self._subscribers.append(adapter)

    def register_publisher(self, adapter):
        if adapter not in self._publishers:
            self._publishers.append(adapter)

    def _get_user_from_id(self, user_id):
        # try to get from cache
        user = self._user_id_to_user.get(user_id, None)

        if not user:
            # try to pull from discord
            user = self._discord_client.get_user(user_id)
            if not user:
                raise ValueError(f"User with id {user_id} not found")
            self._user_id_to_user[user_id] = user
        return user

    def _get_user_from_name(self, user_name):
        # try to pull from cache
        user = self._user_name_to_user_id.get(user_name, None)

        if not user:
            # try to pull from discord
            user = get(self._discord_client.get_all_members(), name=user_name)
            if not user:
                raise ValueError(f"User with name {user_name} not found")
            self._user_name_to_user_id[user_name] = user
        return user

    def _channel_data_to_channel_kind(self, data) -> str:
        if isinstance(data, DMChannel):
            return "message"
        if isinstance(data, TextChannel):
            return "public"
        return "private"

    def _get_channel_from_id(self, channel_id):
        # try to pull from cache
        channel = self._channel_id_to_channel.get(channel_id, None)
        if not channel:
            # try to pull from discord
            channel = self._discord_client.get_channel(channel_id)
            if not channel:
                raise ValueError(f"Channel with id {channel_id} not found")
            self._channel_id_to_channel[channel_id] = channel
        return channel

    def _get_channel_from_name(self, channel_name):
        # first, see if its a regular name or tagged name
        if channel_name.startswith("<#") and channel_name.endswith(">"):
            # strip out the tag
            channel_name = int(channel_name[2:-1])
            # try to pull from ID cache
            channel = self._get_channel_from_id(channel_name)
        else:
            # try to pull from cache
            channel = self._channel_name_to_channel.get(channel_name, None)

        if not channel:
            # try to pull from discord
            channel = get(self._discord_client.get_all_channels(), name=channel_name)
            if not channel:
                raise ValueError(f"Channel with name {channel_name} not found")
            self._channel_name_to_channel[channel_name] = channel
        return channel

    def _run(self):
        discord_client_thread = Thread(target=self._discord_client.run, args=(self._token,), daemon=True)

        @self._discord_client.event
        async def on_ready():
            while True:
                try:
                    while not self._outqueue.empty():
                        # pull DiscordMessage from queue
                        discord_msg = self._outqueue.get()

                        log.debug(f"Outbound: {discord_msg}")

                        # refactor into discord message
                        # grab channel or DM
                        if hasattr(discord_msg, "channel_id") and discord_msg.channel_id:
                            channel = self._get_channel_from_id(int(discord_msg.channel_id))
                        elif hasattr(discord_msg, "channel") and discord_msg.channel:
                            # TODO DM
                            channel = self._get_channel_from_name(discord_msg.channel)

                        # pull text or reaction
                        if hasattr(discord_msg, "reaction") and discord_msg.reaction and hasattr(discord_msg, "thread") and discord_msg.thread:
                            # Adding a reaction, so grab the message id and add a reaction
                            message = await channel.fetch_message(int(discord_msg.thread))
                            await message.add_reaction(discord_msg.reaction)
                        elif hasattr(discord_msg, "msg") and discord_msg.msg:
                            # send text to channel
                            # NOTE: discord has a limit of 2000 characters per message
                            if len(discord_msg.msg) > 0:
                                if len(discord_msg.msg) > 2000:
                                    # Attach as file
                                    io = StringIO(discord_msg.msg)
                                    file = File(io, filename="response.md")
                                    await channel.send(file=file)
                                # TODO: use embeds?
                                # elif len(discord_msg.msg) > 2000:
                                #     # Attach as embed
                                #     embedVar = Embed(title="Response", description=discord_msg.msg, color=0x00FF00)
                                #     await channel.send(embed=embedVar)
                                else:
                                    await channel.send(discord_msg.msg)
                        else:
                            # cannot send empty message, log an error
                            log.error(f"Received malformed DiscordMessage instance: {discord_msg}")
                except KeyboardInterrupt:
                    raise
                except Exception:
                    log.exception("Error sending discord message")
                # short sleep
                await asleep(1)

        @self._discord_client.event
        async def on_message(message):
            if message.author == self._discord_client.user:
                # ignore messages from bot
                pass
            else:
                # cache any information we can use to avoid lookups later
                if message.author.id not in self._user_id_to_user:
                    self._user_id_to_user[message.author.id] = message.author
                if message.author.name not in self._user_name_to_user:
                    self._user_name_to_user[message.author.name] = message.author
                if message.channel.id not in self._channel_id_to_channel:
                    self._channel_id_to_channel[message.channel.id] = message.channel
                # cache channel by recipient name/id for DMs
                if isinstance(message.channel, DMChannel):
                    user_id = message.author.id
                    self._channel_id_to_channel[user_id] = message.channel
                    # NOTE: store as a string because we expect channel names to be strings
                    self._channel_name_to_channel[str(message.channel.id)] = message.channel
                    # NOTE: store as a string because we expect channel names to be strings
                    self._channel_name_to_channel[str(user_id)] = message.channel
                    self._channel_name_to_channel[message.author.name] = message.channel
                if isinstance(message.channel, TextChannel) and message.channel.name not in self._channel_name_to_channel:
                    self._channel_name_to_channel[message.channel.name] = message.channel

                log.debug(f"Inbound: {message}")

                # assemble message
                # NOTE: for parity with slack, we replace the <@USERID> mentions with
                # the actual user name
                discord_msg = message.content
                for mention in message.mentions:
                    discord_msg = discord_msg.replace(f"<@{mention.id}>", f"<@{mention.name}>")
                msg = DiscordMessage(
                    user=message.author.name,
                    user_email="",
                    user_id=str(message.author.id),
                    tags=[str(member.id) for member in message.mentions],
                    channel="IM" if isinstance(message.channel, DMChannel) else message.channel.name,  # NOTE: matches symphony/slack
                    channel_id=str(message.channel.id),
                    channel_type=self._channel_data_to_channel_kind(message.channel),
                    msg=discord_msg,
                    reaction="",
                    thread=str(message.thread.id) if message.thread else str(message.id),
                    payload=message,
                )

                # push message to inqueue
                self._inqueue.put(msg)

        # start the discord client
        discord_client_thread.start()

        while self._running:
            if not self._inqueue.empty():
                # pull all DiscordMessages from queue
                # do as burst to match SymphonyAdapter
                discord_msgs = []
                while not self._inqueue.empty():
                    discord_msgs.append(self._inqueue.get())

                # push to all the subscribers
                for adapter in self._subscribers:
                    adapter.push_tick(discord_msgs)

            # do short sleep
            sleep(0.1)

            # liveness check
            if not discord_client_thread.is_alive():
                self._running = False
                discord_client_thread.join()
                raise Exception("Discord client thread died unexpectedly")

        # shut down client
        self._discord_client.close()

    def _on_tick(self, value):
        self._outqueue.put(value)


class DiscordInputAdapterImpl(PushInputAdapter):
    def __init__(self, manager):
        manager.register_subscriber(self)
        super().__init__()


class DiscordOutputAdapterImpl(OutputAdapter):
    def __init__(self, manager):
        manager.register_publisher(self)
        self._manager = manager
        super().__init__()

    def on_tick(self, time, value):
        self._manager._on_tick(value)


_discord_input_adapter = py_push_adapter_def(
    name="DiscordInputAdapter",
    adapterimpl=DiscordInputAdapterImpl,
    out_type=ts[[DiscordMessage]],
    manager_type=DiscordAdapterManager,
)
_discord_output_adapter = py_output_adapter_def(
    name="DiscordOutputAdapter",
    adapterimpl=DiscordOutputAdapterImpl,
    manager_type=DiscordAdapterManager,
    input=ts[DiscordMessage],
)
