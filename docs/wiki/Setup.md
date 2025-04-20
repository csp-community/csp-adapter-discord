This guide will help you setup a new Discord application.

> [!TIP]
> Find relevant docs with GitHub’s search function, use `repo:csp-community/csp-adapter-discord type:wiki <search terms>` to search the documentation Wiki Pages.

# Discord Configuration

Create a Discord app on the [Discord App portal](https://discord.com/developers/applications).

## General Information

Set your app's "Name".
This is required for the csp chat bot framework.

## OAuth2

Navigate to `Settings->OAuth2` in the newly created app menu.

In the `OAuth2 URL Generator` panel, check `messages.read` in the center column and `bot` in the rightmost column of the `SCOPES` checkbox list.

Then in the `BOT PERMISSIONS` checkbox list that appears, check the following items:

- `View Channels`
- `Send Messages`
- `Send Messages in Threads`
- `Attach Files`
- `Mention Everyone`
- `Add Reactions`

Copy and past the `GENERATED URL` link that is generated to install the bot in your channel.

## Bot

Navigate to `Settings->Bot` in the newly created app menu.

Ensure that `MESSAGE CONTENT INTENT` is checked.

Reset your token under the `TOKEN` section and copy this securely.

# Managing tokens

You should have an `token` from the above steps.

These can be configured directly on the `DiscordAdapterConfig`:

```python
from csp_adapter_discord import DiscordAdapterConfig

config = DiscordAdapterConfig(token="YOUR TOKEN")
```

Alternatively, this could be stored in a local file and the configuration will read them:

**.gitignore**

```raw
.token
```

**.token**

```raw
<YOUR TOKEN>
```

```python
from csp_adapter_discord import DiscordAdapterConfig

config = DiscordAdapterConfig(token=".token")
```
