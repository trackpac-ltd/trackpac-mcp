# VS Code / GitHub Copilot

[← Back to client setup](../README.md#client-setup)

Connect to `https://mcp.trackpac.io/mcp` with your [Trackpac API key](../README.md#getting-an-api-key).

Use the **Install in VS Code** button in the [README](../README.md#quick-start), or open the Command Palette and run **MCP: Open User Configuration** for all projects. For one project, create `.vscode/mcp.json` with this configuration:

```json
{
  "servers": {
    "trackpac": {
      "type": "http",
      "url": "https://mcp.trackpac.io/mcp",
      "headers": {
        "X-API-Key": "${input:trackpacApiKey}"
      }
    }
  },
  "inputs": [
    {
      "type": "promptString",
      "id": "trackpacApiKey",
      "description": "Trackpac API key",
      "password": true
    }
  ]
}
```

Start the server and enter your key in the password prompt. Open Copilot Chat, select an agent mode that supports tools, and enable the Trackpac tools. See [VS Code's MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).
