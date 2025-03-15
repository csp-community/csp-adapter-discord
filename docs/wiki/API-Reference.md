# Adapter Config

`DiscordAdapterConfig` requires:

- `token`: Discord Bot Token

See [Setup](Setup) for more information.

# Adapter Manager

`DiscordAdapterManager` takes a single argument `config`, an instance of `DiscordAdapterConfig`.
It provides two methods:

- `subscribe() -> ts[[DiscordMessage]]`: Subscribe to messages (`DiscordMessage`) from channels in which the Bot is present, and DMs
- `publish(ts[DiscordMessage])`: Publish messages (`DiscordMessage`)

> [!NOTE]
>
> `subscribe` returns a list of `DiscordMessage`, but `publish` takes an individual `DiscordMessage`.
> This is for API symmetry with the [csp-adapter-symphony](https://github.com/point72/csp-adapter-symphony).
> `csp.unroll` can be used to unroll the list of `ts[List[DiscordMessage]]` into `ts[DiscordMessage]`.

```python
from csp_adapter_discord import DiscordAdapterConfig, DiscordAdapterManager


def graph():
    adapter = DiscordAdapterManager(
      config=DiscordMessage(token="YOUR TOKEN"),
    )

    csp.print("All Messages", adapter.subscribe())
```

See [Examples](Examples) for more examples.

# Chat Framework

`csp-chat` is a framework for writing cross-platform, command oriented chat bots.
It will be released in 2025 with initial support for `Slack`, `Symphony`, and `Discord`.
