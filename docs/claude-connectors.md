# Claude connectors (web and Desktop)

[← Back to client setup](../README.md#client-setup)

## OAuth connection

This option requires an OAuth-enabled Trackpac endpoint. Once your deployment operator enables Trackpac sign-in, you can connect without Node.js, a JSON file, or an API key:

1. Open **Customize → Connectors → Add custom connector** in Claude Desktop or at [claude.ai](https://claude.ai). On Team or Enterprise, an owner adds it in **Organization settings → Connectors**.
2. Name it **Trackpac**, enter `https://mcp.trackpac.io/mcp`, and continue.
3. Choose **Sign in now**. Keep automatic OAuth client registration or Claude's published identity selected; no Auth0 client secret is needed in the connector dialog.
4. Add/connect the connector and complete the Trackpac login and consent prompts.
5. Enable Trackpac under **+ → Connectors** in a chat and ask **"List my Trackpac devices."**

## API-key connection (limited beta)

Claude's custom connectors can send API keys through **Request headers**. Anthropic currently limits this feature to a beta for some organizations. If your connector dialog has that section, no Node.js or JSON file is needed:

1. Open **Customize → Connectors → Add custom connector** in Claude Desktop or at [claude.ai](https://claude.ai). For Team or Enterprise, an owner adds the connector in **Organization settings → Connectors**.
2. Name it **Trackpac** and enter `https://mcp.trackpac.io/mcp`.
3. Choose **No sign-in** under Authentication.
4. Under **Request headers**, select `x-api-key`, enter your Trackpac API key as the value, and mark it required.
5. Save, enable Trackpac in your chat's **+ → Connectors** menu, and ask **"List my Trackpac devices."**

On Team and Enterprise, this fixed key is shared by everyone using that connector. Use OAuth when each person must authenticate separately. If **Request headers** is missing, use the [Claude Desktop bridge](claude-desktop.md). OAuth requires Trackpac sign-in to be enabled on the endpoint.

Source: [Anthropic's custom connector and request-header guide](https://claude.com/docs/connectors/custom/add-unlisted#authenticate-with-request-headers).
