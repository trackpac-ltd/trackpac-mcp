# Codex (CLI and IDE extension)

[← Back to client setup](../README.md#client-setup)

Connect to `https://mcp.trackpac.io/mcp` with your [Trackpac API key](../README.md#getting-an-api-key).

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.trackpac]
url = "https://mcp.trackpac.io/mcp"

[mcp_servers.trackpac.http_headers]
X-API-Key = "YOUR_TRACKPAC_API_KEY"
```

Alternatively, keep the key in the environment available to Codex and use this header configuration instead of `http_headers`:

```toml
[mcp_servers.trackpac.env_http_headers]
X-API-Key = "TRACKPAC_API_KEY"
```

Restart your Codex client after changing its configuration. See [OpenAI's MCP documentation](https://developers.openai.com/codex/mcp).
