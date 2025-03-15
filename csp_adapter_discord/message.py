from typing import List, Optional

from csp.impl.struct import Struct
from discord import Message

__all__ = ("DiscordMessage",)


class DiscordMessage(Struct):
    user: str
    user_email: str  # email of the author
    user_id: str  # user id of the author
    tags: List[str]  # list of mentions

    channel: str  # name of channel
    channel_id: str  # id of channel
    channel_type: str  # type of channel, in "message", "public" (app_mention), "private" (app_mention)

    msg: str  # parsed text payload
    reaction: str  # emoji reacts
    thread: str  # thread id, if in thread
    payload: Optional[Message] = None  # raw message payload
