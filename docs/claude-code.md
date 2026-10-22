# Claude Code

[← Back to client setup](../README.md#client-setup)

Connect to `https://mcp.trackpac.io/mcp` with your [Trackpac API key](../README.md#getting-an-api-key).

Run this in your terminal to make Trackpac available across your projects:

```bash
claude mcp add --transport http --scope user trackpac https://mcp.trackpac.io/mcp \
  --header "X-API-Key: YOUR_TRACKPAC_API_KEY"
```

Run `/mcp` inside Claude Code to check the connection. See [Claude Code's MCP documentation](https://code.claude.com/docs/en/mcp).
