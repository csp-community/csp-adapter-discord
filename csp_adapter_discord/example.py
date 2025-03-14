import csp
from csp import ts

from csp_adapter_discord import DiscordAdapterConfig, DiscordAdapterManager, DiscordMessage

# Create a DiscordAdapterConfig object
config = DiscordAdapterConfig(
    # Your Discord bot token
    token=".token",
    # The prefix for your bot commands
)


@csp.node
def add_reaction_when_mentioned(msg: ts[DiscordMessage]) -> ts[DiscordMessage]:
    return DiscordMessage(
        channel=msg.channel,
        thread=msg.thread,
        reaction="👋",
    )


def graph():
    # Create a DiscordAdapter object
    adapter = DiscordAdapterManager(config)
    msgs = csp.unroll(adapter.subscribe())
    csp.print("msgs:", msgs)
    reactions = add_reaction_when_mentioned(msgs)
    csp.print("reactions:", reactions)
    adapter.publish(reactions)


if __name__ == "__main__":
    csp.run(graph, realtime=True)
