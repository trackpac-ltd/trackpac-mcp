# Claude connectors (web and Desktop)

[← Back to client setup](../README.md#client-setup)

Claude's custom connectors can send API keys through **Request headers**. Anthropic currently limits this feature to a beta for some organizations. If your connector dialog has that section, no Node.js or JSON file is needed:

1. Open **Customize → Connectors → Add custom connector** in Claude Desktop or at [claude.ai](https://claude.ai). For Team or Enterprise, an owner adds the connector in **Organization settings → Connectors**.
2. Name it **Trackpac** and enter `https://mcp.trackpac.io/mcp`.
3. Choose **No sign-in** under Authentication.
4. Under **Request headers**, select `x-api-key`, enter your Trackpac API key as the value, and mark it required.
5. Save, enable Trackpac in your chat's **+ → Connectors** menu, and ask **"List my Trackpac devices."**

On Team and Enterprise, this fixed key is shared by everyone using that connector. Use OAuth when each person must authenticate separately. If **Request headers** is missing, use the [Claude Desktop bridge](claude-desktop.md). Trackpac does not offer OAuth yet.

Source: [Anthropic's custom connector and request-header guide](https://claude.com/docs/connectors/custom/add-unlisted#authenticate-with-request-headers).
