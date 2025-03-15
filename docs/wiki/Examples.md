The below examples are available [in-source](https://github.com/timkpaine/csp-adapter-discord/blob/main/csp_adapter_discord/examples/).
They assume the presence of a `.token` file in the run directory.
Additionally, they assume all optional settings in [Setup](Setup) have been enabled.

# Emoji Wave

Here is a simple example that waves when someone says `hello` in a room or direct message to the bot.
It is available in-source at [`csp_adapter_discord/examples/hello.py`](https://github.com/timkpaine/csp-adapter-discord/blob/main/csp_adapter_discord/examples/hello.py).

```python
import csp
from csp import ts

from csp_adapter_discord import DiscordAdapterConfig, DiscordAdapterManager, DiscordMessage

config = DiscordAdapterConfig(token=".token")


@csp.node
def add_reaction_when_mentioned(msg: ts[DiscordMessage]) -> ts[DiscordMessage]:
    """Add a reaction to every message to the bot that starts with hello."""
    if "hello" in msg.msg.lower():
        return DiscordMessage(
            channel=msg.channel,
            thread=msg.thread,
            reaction="👋",
        )


def graph():
    # Create a DiscordAdapter object
    adapter = DiscordAdapterManager(config)

    # Subscribe and unroll the messages
    msgs = csp.unroll(adapter.subscribe())

    # Print it out locally for debugging
    csp.print("msgs", msgs)

    # Add the reaction node
    reactions = add_reaction_when_mentioned(msgs)

    # Print it out locally for debugging
    csp.print("reactions", reactions)

    # Publish the reactions
    adapter.publish(reactions)


if __name__ == "__main__":
    csp.run(graph, realtime=True)

```
