# Trackpac MCP Server

An [MCP](https://modelcontextprotocol.io) server for the
[Trackpac](https://trackpac.io) IoT platform. It lets Claude, ChatGPT, or any
other MCP client work with your Trackpac account in plain language: list devices, read
recent frames, manage geofences, dashboards, assets, actions, reports, contacts
and more.

> "Which of my trackers haven't reported in the last 24 hours?"
> "Create a geofence around our Rotterdam depot and alert the ops contact on exit."
> "Show me the last week of location history for asset *Trailer 12*."

## Features

- **Full API coverage** of the Trackpac REST API (`https://api.trackpac.io`):
  users and API keys, organisations, devices, frames, dashboards, assets,
  reports, actions, contacts, geofences, bases, tags, LNS, billing and the
  LoRaWAN location engine.
- **Always in sync.** Tools are generated at startup from Trackpac's live
  [OpenAPI spec](https://api.trackpac.io/openapi.json) using
  [FastMCP](https://gofastmcp.com), so new API endpoints show up after a restart
  with no code changes.
- **API-key authentication.** Requests are sent with your key in the
  `X-API-Key` header.
- **Thin pass-through.** There is no extra caching, retry logic or rate
  limiting, so your account's normal Trackpac permissions and limits apply.

## Requirements

- Python 3.10 or newer
- A Trackpac account and an API key (see [Getting an API key](#getting-an-api-key))

## Installation

```bash
git clone https://github.com/trackpac-ltd/trackpac-mcp.git
cd trackpac-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Getting an API key

1. Sign in to Trackpac and open your account page:
   **<https://app.trackpac.io/account>**
2. Click **Generate API key**.
3. Give the key a name that tells you where it's used, for example
   `Claude Desktop - laptop`.
4. Copy the key and keep it somewhere safe, such as a password manager. You'll
   paste it into your MCP client's config in the next step.

The key has the same access as your Trackpac user, so treat it like a password.
Never commit it to git or share it in chat. If a key is ever exposed, revoke it
on the same account page and generate a new one.

It's a good idea to create a separate key for each machine or client. That way
you can revoke one without breaking the others.

## Configuration

The server reads a single environment variable:

| Variable           | Required | Description           |
| ------------------ | -------- | --------------------- |
| `TRACKPAC_API_KEY` | Yes      | Your Trackpac API key |

You can set it in your MCP client's config (recommended, see below). For local
testing, you can instead copy `.env.example` to `.env` and export it in your
shell.

## Using it with Claude

### Claude Code

```bash
claude mcp add trackpac --env TRACKPAC_API_KEY=your-key -- /absolute/path/to/trackpac-mcp/.venv/bin/python /absolute/path/to/trackpac-mcp/server.py
```

### Claude Desktop

Add the server to your `claude_desktop_config.json` (an example is in
[`claude_desktop_config.example.json`](claude_desktop_config.example.json)):

```json
{
  "mcpServers": {
    "trackpac": {
      "command": "/absolute/path/to/trackpac-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/trackpac-mcp/server.py"],
      "env": {
        "TRACKPAC_API_KEY": "your-trackpac-api-key-here"
      }
    }
  }
}
```

Restart Claude Desktop after you save the file.

## Using it with ChatGPT and OpenAI Codex

### Codex (CLI and IDE extension)

Codex runs local MCP servers the same way Claude does. Add the server with:

```bash
codex mcp add trackpac --env TRACKPAC_API_KEY=your-key -- /absolute/path/to/trackpac-mcp/.venv/bin/python /absolute/path/to/trackpac-mcp/server.py
```

Or add it to `~/.codex/config.toml` yourself:

```toml
[mcp_servers.trackpac]
command = "/absolute/path/to/trackpac-mcp/.venv/bin/python"
args = ["/absolute/path/to/trackpac-mcp/server.py"]

[mcp_servers.trackpac.env]
TRACKPAC_API_KEY = "your-trackpac-api-key-here"
```

### ChatGPT (web)

ChatGPT can't start a program on your computer. It only connects to **remote**
MCP servers over HTTPS, so you run this server in HTTP mode and give ChatGPT a
way to reach it.

**Before you start**

- **Plan:** Custom MCP servers with full read and write access are available on
  ChatGPT **Business**, **Enterprise** and **Edu**. On Business, only workspace
  admins and owners can add them. On Enterprise and Edu, admins can grant the
  permission to other members. **Pro** users can connect custom servers with
  read/fetch access only, so tools that create, update or delete won't work.
- **Web only:** You can't add custom MCP servers in the mobile apps.

> [!WARNING]
> In HTTP mode, the server makes every Trackpac call with **your** API key.
> The server has no login of its own, so **anyone who can reach its URL can read
> and change your Trackpac account**. Don't put it on the public internet without
> authentication in front of it. The Secure MCP Tunnel option below avoids this.

**1. Run the server in HTTP mode**

```bash
cd trackpac-mcp
source .venv/bin/activate
TRACKPAC_API_KEY=your-key fastmcp run server.py --transport http --port 8000
```

The MCP endpoint is now at `http://127.0.0.1:8000/mcp`.

**2. Let ChatGPT reach it.** Choose one option:

- **Secure MCP Tunnel (recommended).** OpenAI's tunnel connects ChatGPT to a
  server on your own machine or private network without exposing it to the
  internet:
  1. Create a tunnel in your OpenAI Platform organisation's tunnel settings and
     note its tunnel ID. You need Platform permissions to manage tunnels, so
     ask your org admin if you can't see the settings.
  2. Run OpenAI's `tunnel-client` on the same machine as the server and point
     it at `http://127.0.0.1:8000/mcp`. It only needs outbound HTTPS access to
     `api.openai.com:443`.

  See OpenAI's
  [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
  for the full steps.
- **Public HTTPS URL.** Deploy the server somewhere with HTTPS, such as a cloud
  VM or container platform, and put authentication in front of it (for
  example an OAuth-capable gateway). Use the full URL including `/mcp`, for
  example `https://trackpac-mcp.example.com/mcp`.

**3. Add the server in ChatGPT**

1. Open [chatgpt.com](https://chatgpt.com) and go to **Plugins**.
2. Select the **+** button, then **Add custom MCP server**.
3. Enter a name, for example `Trackpac`, and optionally a description.
4. Under **Connection**, either enter your public HTTPS endpoint URL, or select
   **Tunnel** and pick your Secure MCP Tunnel (or paste its tunnel ID).
5. Configure authentication to match how you protected the server.
6. Read the risk warning and tick **I understand and want to continue**.
7. Select **Create as a plugin** and check the list of discovered Trackpac
   tools.

**4. Use it**

Install the plugin, start a new chat, type **@**, select **Trackpac**, and ask
your question. ChatGPT asks you to confirm before it runs write actions.

**Good to know**

- **Tool list is frozen after approval.** In Business and Enterprise
  workspaces, ChatGPT keeps the tool list from when an admin approved the
  server. When the Trackpac API adds or changes endpoints, an admin needs to
  refresh the tools from the workspace app settings.
- **Deep research is read-only.** Deep research can use the server for read
  requests only, not write actions.

OpenAI's full guide:
[Connecting custom MCP servers in ChatGPT](https://help.openai.com/en/articles/12584461).

## Other MCP clients

Run the server over stdio (the default):

```bash
TRACKPAC_API_KEY=your-key python server.py
```

Or over HTTP for clients that connect by URL:

```bash
TRACKPAC_API_KEY=your-key fastmcp run server.py --transport http --port 8000
```

The endpoint is `http://127.0.0.1:8000/mcp`.

## Tools

Each tool maps to one Trackpac API endpoint, and its name comes from the
endpoint's OpenAPI `operationId`. For example:

| Tool                                 | What it does                      |
| ------------------------------------ | --------------------------------- |
| `get_organisations_organisation_get` | List your organisations           |
| `read_devices_device_get`            | List devices                      |
| `read_frames_frame`                  | Read uplink frames for a device   |
| `create_geofence_geofence_post`      | Create a geofence                 |
| `send_downlink_device`               | Queue a downlink to a device      |

As of Trackpac API v2.5.15 the server exposes about 150 tools. Your MCP client
lists the exact set when it connects.

### Excluded endpoints

Some endpoints exist only for machine-to-machine traffic, not for people, so
the server leaves them out. The main example is `/ingest/*`, the webhook
endpoints where LoRaWAN network servers and hardware send raw sensor payloads.

## Safety

The server exposes **write and delete operations** as well as reads (for
example `delete_device_device` and `delete_organisation_organisation`). Your
assistant can do anything your API key allows.

- Use a key from a user with only the access you need.
- Keep your MCP client's tool-approval prompts turned on for destructive
  actions.
- Start with read-only requests while you get familiar with it.

## Customising

All the logic lives in [`server.py`](server.py):

- **Exclude more endpoints**: add tags to `EXCLUDED_TAGS`, path prefixes to
  `EXCLUDED_PATH_PREFIXES`, or path keywords to `EXCLUDED_PATH_KEYWORDS`.
- **Reduce the tool count**: change `route_maps` so `GET` endpoints become MCP
  resources (`MCPType.RESOURCE` / `MCPType.RESOURCE_TEMPLATE`) instead of tools.
  This roughly halves the tool list. It's handy if your client struggles with
  long tool lists, but some assistants work less reliably with resources.

## How it works

At startup, `server.py`:

1. Fetches `https://api.trackpac.io/openapi.json`.
2. Removes the excluded webhook routes.
3. Passes the spec to `FastMCP.from_openapi()` with an HTTP client that carries
   your API key.

Restart the server to pick up API changes.

## Contributing

Issues and pull requests are welcome.
