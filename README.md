# trackpac-mcp

An MCP server for the Trackpac API (`https://api.trackpac.io`), so Claude (or
any other MCP client) can query and manage your devices, organisations,
dashboards, assets, geofences, actions, reports, contacts, bases, tags and
billing directly.

It's built automatically from Trackpac's own OpenAPI spec
(`https://api.trackpac.io/openapi.json`) using [FastMCP](https://gofastmcp.com)'s
`from_openapi()` — every request/response shape comes straight from the spec,
so it stays in sync with the real API without hand-written wrapper code.

## What's excluded, and why

- **`/ingest/*` (tag `Ingest`, ~90 routes)** — the per-device-brand webhook
  endpoints that LoRaWAN network servers / hardware POST raw sensor payloads
  to. Not something a person or assistant would ever call, so they're
  stripped before the tool list is built (as requested).

Everything else — devices, organisations, dashboards, assets, reports,
actions, contacts, geofences, bases, billing (account-facing bits), tags,
frames, the location engine, and user/API-key management — is exposed. As of
the spec's current version (Trackpac API v2.5.15) that's **148 tools**. This
includes both reads and writes (e.g. `delete_device_device`,
`delete_organisation_organisation` exist) — there's no separate read-only
mode, so treat the API key you give this server with the same care as one
in the Trackpac dashboard.

If 148 tools feels like too many for your MCP client's tool picker, the
easiest reduction is to change the `route_maps` in `server.py` so read-only
`GET` requests become MCP *resources* instead of *tools* (FastMCP supports
this natively via `MCPType.RESOURCE` / `RESOURCE_TEMPLATE`) — that would cut
the tool list roughly in half while keeping the data still reachable. Left
as everything-is-a-tool for now since that's the most reliable way for a
chat assistant to actually call these with arguments.

## Setup

1. **Install dependencies** (Python 3.10+):

   ```bash
   cd trackpac-mcp
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Get an API key.** This server is API-key-only — it sends `X-API-Key` on
   every request and never uses a bearer token, even though the Trackpac API
   itself accepts both. Create a key from the Trackpac dashboard's API keys
   settings page (or however you normally provision one). If your account
   doesn't have a key yet and the dashboard doesn't offer a way to create
   one, you'll need to get your first key through whatever authenticated
   flow Trackpac normally uses for that (this server intentionally won't do
   that bootstrapping step for you, to keep it API-key-only end to end).

3. **Set the credential** — copy `.env.example` to `.env` and fill in
   `TRACKPAC_API_KEY`, or set it directly in your MCP client's server config
   (see below).

4. **Run it standalone** (useful for a sanity check):

   ```bash
   TRACKPAC_API_KEY=your-key python server.py
   ```

## Wiring it into Claude

**Claude Code / Claude CLI:**

```bash
claude mcp add trackpac --env TRACKPAC_API_KEY=your-key -- python /absolute/path/to/trackpac-mcp/server.py
```

**Claude Desktop:** add an entry like the one in
`claude_desktop_config.example.json` to your
`claude_desktop_config.json`, with the real absolute path to `server.py` and
your key.

## How it works / notes

- `server.py` fetches `https://api.trackpac.io/openapi.json` live at
  startup, strips the excluded routes, and hands the result to
  `FastMCP.from_openapi()` along with an `httpx` client carrying your auth
  header. Restart the server to pick up any API changes.
- Tool names come from the spec's `operationId`s (FastMCP slugifies them),
  e.g. `read_devices_organisation`, `create_geofence_geofence_post`,
  `send_downlink_device`. They're a little verbose but self-describing.
- No response caching, rate limiting, or retry logic is added — this is a
  thin, faithful pass-through to the real API, so normal Trackpac rate
  limits and permissions apply.
- Validated during development by fetching the live spec and confirming it
  builds cleanly into 148 tools with the ingest/webhook routes removed and
  everything else intact (grouped by the API's own tags: Users,
  Organisations, Devices, Frames, Dashboards, Assets, Reports, LoRaWAN
  Location Engine, Actions, Contacts, Geofences, Bases, Billing, Tags, LNS).
  Full end-to-end calls against live data weren't exercised (no API key was
  available in the build environment) — worth doing a couple of read-only
  calls (e.g. list your organisations) first, before relying on it for
  anything that writes.
