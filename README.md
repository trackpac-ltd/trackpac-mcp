# Trackpac MCP Server

An [MCP](https://modelcontextprotocol.io) server for the [Trackpac](https://trackpac.io) IoT platform. It lets Claude, Codex, and other MCP clients work with your Trackpac account in plain language: list devices, read recent frames, manage geofences, dashboards, assets, actions, reports, contacts and more.

> "Which of my trackers haven't reported in the last 24 hours?"
> "Create a geofence around our Rotterdam depot and alert the ops contact on exit."
> "Show me the last week of location history for asset *Trailer 12*."

## Quick start

1. [Get a Trackpac API key](#getting-an-api-key).
2. Choose your client below and connect to **`https://mcp.trackpac.io/mcp`**.
3. Ask: "List my Trackpac devices."

Use our hosted server without cloning this repository or installing Python. The transport is **Streamable HTTP**, and each client sends its own key in the **`X-API-Key`** header.

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_Trackpac-007ACC?style=for-the-badge)](https://vscode.dev/redirect/mcp/install?%7B%22name%22%3A%22trackpac%22%2C%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fmcp.trackpac.io%2Fmcp%22%2C%22headers%22%3A%7B%22X-API-Key%22%3A%22%24%7Binput%3AtrackpacApiKey%7D%22%7D%2C%22inputs%22%3A%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22trackpacApiKey%22%2C%22description%22%3A%22Trackpac%20API%20key%22%2C%22password%22%3Atrue%7D%5D%7D)
[![Add to Cursor](https://img.shields.io/badge/Cursor-Add_Trackpac-181818?style=for-the-badge)](https://cursor.com/en/install-mcp?name=trackpac&config=eyJ1cmwiOiJodHRwczovL21jcC50cmFja3BhYy5pby9tY3AiLCJoZWFkZXJzIjp7IlgtQVBJLUtleSI6IllPVVJfVFJBQ0tQQUNfQVBJX0tFWSJ9fQ%3D%3D)

VS Code prompts for your API key when the server starts. After installing in Cursor, replace `YOUR_TRACKPAC_API_KEY` in the server configuration with your key before using it. The buttons contain no credentials.

[Choose your client](#client-setup) for detailed instructions, including Claude Desktop.

## Getting an API key

1. Sign in to Trackpac and open your account page: **<https://app.trackpac.io/account>**
2. Click **Generate API key**.
3. Give the key a name that tells you where it's used, for example `Claude Desktop - laptop`.
4. Copy the key and keep it somewhere safe, such as a password manager. You'll paste it into your MCP client's config in the next step.

The key has the same access as your Trackpac user, so treat it like a password. Never commit it to git or share it in chat. If a key is ever exposed, revoke it on the same account page and generate a new one.

It's a good idea to create a separate key for each machine or client. That way you can revoke one without breaking the others.

## Client setup

Choose your client for step-by-step hosted setup:

| Client | Setup |
| --- | --- |
| [Claude Desktop](docs/claude-desktop.md) | Local bridge using Node.js and a JSON config |
| [Claude connectors (web and Desktop)](docs/claude-connectors.md) | Direct hosted connection; requires request-header beta |
| [Claude Code](docs/claude-code.md) | One terminal command |
| [VS Code / GitHub Copilot](docs/vscode.md) | Install button or JSON configuration |
| [Cursor](docs/cursor.md) | Install button or JSON configuration |
| [Codex](docs/codex.md) | TOML configuration |
| [ChatGPT](docs/chatgpt.md) | Requires OAuth; not supported by the hosted server yet |

## Troubleshooting

- **Claude Desktop setup or bridge errors:** see the [Claude Desktop guide](docs/claude-desktop.md).
- **Tools appear but calls return 401 or 403:** confirm the API key is valid and the header name is `X-API-Key`. Your Trackpac user's permissions apply to every request.
- **The URL shows an error in a browser:** this is an MCP protocol endpoint, not a web page. Test it through your MCP client using the full `/mcp` URL.

## Features

- **Full API coverage** of the Trackpac REST API (`https://api.trackpac.io`): users and API keys, organisations, devices, frames, dashboards, assets, reports, actions, contacts, geofences, tags, LNS, billing and the LoRaWAN location engine.
- **Always in sync.** Tools are generated at startup from Trackpac's live [OpenAPI spec](https://api.trackpac.io/openapi.json) using [FastMCP](https://gofastmcp.com), so new API endpoints show up after a restart with no code changes.
- **API-key authentication.** Requests are sent with your key in the `X-API-Key` header.
- **Thin pass-through.** There is no extra caching, retry logic or rate limiting, so your account's normal Trackpac permissions and limits apply.

## Self-hosting and local development

Hosted users can skip this section. To run your own server, install Python 3.10 or newer and clone the repo:

```bash
git clone https://github.com/trackpac-ltd/trackpac-mcp.git
cd trackpac-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Server configuration

| Variable | Required | Description |
| --- | --- | --- |
| `TRACKPAC_API_KEY` | For stdio; omit for shared HTTP hosting | Your Trackpac API key. When set, it takes precedence over callers' `X-API-Key` headers. |
| `TRACKPAC_API_URL` | No | Defaults to `https://api.trackpac.io`; can point to staging or a local API. |

For local testing, you can copy `.env.example` to `.env` and export its values in your shell. The server does not automatically load `.env` files.

### Local stdio

```bash
TRACKPAC_API_KEY=your-key python server.py
```

Clients can start it directly. For example, Claude Code:

```bash
claude mcp add trackpac-local --env TRACKPAC_API_KEY=your-key -- /absolute/path/to/trackpac-mcp/.venv/bin/python /absolute/path/to/trackpac-mcp/server.py
```

Or use this local configuration in Claude Desktop instead of the hosted bridge:

```json
{
  "mcpServers": {
    "trackpac-local": {
      "command": "/absolute/path/to/trackpac-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/trackpac-mcp/server.py"],
      "env": {
        "TRACKPAC_API_KEY": "YOUR_TRACKPAC_API_KEY"
      }
    }
  }
}
```

### HTTP hosting

Start without `TRACKPAC_API_KEY` for a shared deployment:

```bash
fastmcp run server.py --transport http --host 0.0.0.0 --port 8000
```

The endpoint is `http://localhost:8000/mcp`. Each caller sends their own `X-API-Key` header, which FastMCP forwards to the Trackpac API. The API checks the key and applies that user's permissions. Put HTTPS in front of the server for public hosting, and replace the hosted URL in the client examples with your own endpoint.

**Leave `TRACKPAC_API_KEY` unset on shared deployments.** Setting it gives callers access through the server's configured key, so a deployment with a fixed key needs authentication and access controls in front of it.

### Docker

CI publishes an image to `ghcr.io/trackpac-ltd/trackpac-mcp` on every push to `main` (tagged `latest` and `sha-<commit>`) and on version tags such as `v1.2.0`. It runs the server in HTTP mode on port 8000:

```bash
docker run --rm -p 8000:8000 ghcr.io/trackpac-ltd/trackpac-mcp
```

Each caller supplies their own `X-API-Key` header. To build the image yourself, run `docker build -t trackpac-mcp .`.

## Tools

Each tool maps to one Trackpac API endpoint, and its name comes from the endpoint's OpenAPI `operationId`. For example:

| Tool                                 | What it does                      |
| ------------------------------------ | --------------------------------- |
| `get_organisations_organisation_get` | List your organisations           |
| `read_devices_device_get`            | List devices                      |
| `read_frames_frame`                  | Read uplink frames for a device   |
| `create_geofence_geofence_post`      | Create a geofence                 |
| `send_downlink_device`               | Queue a downlink to a device      |

The server currently exposes about 130 tools. The exact number changes as the Trackpac API evolves, and your MCP client lists the full set when it connects.

### Excluded endpoints

Some endpoints exist only for machine-to-machine traffic, not for people, so the server leaves them out. The main example is `/ingest/*`, the webhook endpoints where LoRaWAN network servers and hardware send raw sensor payloads.

The legacy **bases** endpoints are left out too. Use geofences instead.

## Safety

The server exposes **write and delete operations** as well as reads (for example `delete_device_device` and `delete_organisation_organisation`). Your assistant can do anything your API key allows.

- Use a key from a user with only the access you need.
- Keep your MCP client's tool-approval prompts turned on for destructive actions.
- Start with read-only requests while you get familiar with it.

## Customising

All the logic lives in [`server.py`](server.py):

- **Exclude more endpoints**: add tags to `EXCLUDED_TAGS`, path prefixes to `EXCLUDED_PATH_PREFIXES`, or path keywords to `EXCLUDED_PATH_KEYWORDS`.
- **Reduce the tool count**: change `route_maps` so `GET` endpoints become MCP resources (`MCPType.RESOURCE` / `MCPType.RESOURCE_TEMPLATE`) instead of tools. This roughly halves the tool list. It's handy if your client struggles with long tool lists, but some assistants work less reliably with resources.

## How it works

At startup, `server.py`:

1. Fetches `https://api.trackpac.io/openapi.json`.
2. Removes the excluded webhook routes.
3. Passes the spec to `FastMCP.from_openapi()` with an HTTP client that carries your API key.

Restart the server to pick up API changes.

## Contributing

Issues and pull requests are welcome.

Code is formatted with [Black](https://black.readthedocs.io) and linted with [Ruff](https://docs.astral.sh/ruff/), and tested with [pytest](https://docs.pytest.org). CI runs all three on every pull request. To set up the tools and git hooks locally:

```bash
pip install -r requirements-dev.txt
pre-commit install
pytest
```

## License

Copyright 2026 Trackpac Ltd. Licensed under the [Apache License 2.0](LICENSE). The license covers this code only; it grants no rights to the Trackpac name or trademarks, and use of the Trackpac API remains subject to Trackpac's terms of service.
