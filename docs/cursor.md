# Cursor

[← Back to client setup](../README.md#client-setup)

Connect to `https://mcp.trackpac.io/mcp` with your [Trackpac API key](../README.md#getting-an-api-key).

Use the **Add to Cursor** button in the [README](../README.md#quick-start), then replace `YOUR_TRACKPAC_API_KEY` in the installed configuration. Alternatively, create or edit `~/.cursor/mcp.json` for all projects, or `.cursor/mcp.json` in one project:

```json
{
  "mcpServers": {
    "trackpac": {
      "url": "https://mcp.trackpac.io/mcp",
      "headers": {
        "X-API-Key": "YOUR_TRACKPAC_API_KEY"
      }
    }
  }
}
```

Enable Trackpac in Cursor's MCP settings and check that its tools appear. See [Cursor's MCP documentation](https://cursor.com/docs/context/mcp).
