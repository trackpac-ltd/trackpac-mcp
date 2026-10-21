# Trackpac MCP Server

An [MCP](https://modelcontextprotocol.io) server for the
[Trackpac](https://trackpac.io) IoT platform. It lets Claude, or any other MCP
client, work with your Trackpac account in plain language: list devices, read
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
- A Trackpac account and an API key

## Installation

```bash
git clone https://github.com/trackpac-ltd/trackpac-mcp.git
cd trackpac-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Getting an API key

Create an API key in the Trackpac dashboard under your user settings. The key
has the same access as your user account, so keep it private and revoke it from
the dashboard if it is ever exposed.

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

### Other MCP clients

Run the server over stdio:

```bash
TRACKPAC_API_KEY=your-key python server.py
```

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

A few endpoints exist for machine-to-machine traffic, not for people, so the
server leaves them out:

- **`/ingest/*`**: webhook endpoints where LoRaWAN network servers and
  hardware send raw sensor payloads.

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
