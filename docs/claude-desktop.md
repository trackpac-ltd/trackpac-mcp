# Claude Desktop (local bridge)

[← Back to client setup](../README.md#client-setup)

This setup runs a small `mcp-remote` bridge on your computer, which connects Claude Desktop to the hosted Trackpac server. It requires **Node.js LTS**; install it from [nodejs.org](https://nodejs.org) if needed.

1. Open Claude Desktop. On macOS, choose **Claude → Settings…** from the macOS menu bar. On Windows, open the app's **Settings**.
2. Choose **Developer → Edit Config**. Open `claude_desktop_config.json` in a text editor if this opens a folder.
3. Paste the configuration below and replace `YOUR_TRACKPAC_API_KEY` with your [Trackpac API key](../README.md#getting-an-api-key). If you already have MCP servers, add `trackpac` inside the existing `mcpServers` object.
4. Save, fully quit Claude (**Cmd+Q** on macOS), and reopen it. The first launch downloads the bridge automatically.
5. Check **Settings → Developer** for Trackpac's status, enable its tools in your chat if needed, and ask **"List my Trackpac devices."**

```json
{
  "mcpServers": {
    "trackpac": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.trackpac.io/mcp",
        "--header",
        "X-API-Key:${TRACKPAC_API_KEY}"
      ],
      "env": {
        "TRACKPAC_API_KEY": "YOUR_TRACKPAC_API_KEY"
      }
    }
  }
}
```

Keep `${TRACKPAC_API_KEY}` in `args` as written; put your key in the `env` value. A copy is in [the example config](claude_desktop_config.example.json).

## Where is the config file?

- **macOS:** in Finder, press **Cmd+Shift+G** and paste `~/Library/Application Support/Claude`. Open `claude_desktop_config.json`.
- **Windows:** press **Win+R**, enter `%APPDATA%\Claude`, and open `claude_desktop_config.json`.

**Edit Config** creates the file if it is missing. Save it as plain JSON, with no comments or trailing commas.

## If it does not connect

Check the error in **Settings → Developer**. If `npx` is missing, confirm `npx --version` works in your terminal and fully restart Claude. If needed, find its full path with `which npx` (macOS) or `where.exe npx` (Windows) and use that as `command`. Escape Windows backslashes as `\\` in JSON.

For account-wide connections through Claude's UI, see the [Claude connectors guide](claude-connectors.md). OAuth works when enabled by the host; the direct API-key option requires Anthropic's request-header beta.

References: [Claude Desktop configuration](https://modelcontextprotocol.io/docs/develop/connect-local-servers) and [mcp-remote](https://github.com/punkpeye/mcp-remote).
