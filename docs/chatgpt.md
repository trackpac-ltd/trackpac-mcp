# ChatGPT

[← Back to client setup](../README.md#client-setup)

ChatGPT requires an OAuth-enabled Trackpac endpoint. Your deployment operator must enable Trackpac sign-in before you can connect. An API-key-only server cannot authenticate ChatGPT requests because ChatGPT cannot send a custom `X-API-Key` header.

Once the host has enabled OAuth:

1. Open ChatGPT's **Plugins** page and choose **Add custom MCP server**. This option requires access to custom MCP servers in your account or workspace.
2. Name it **Trackpac** and enter `https://mcp.trackpac.io/mcp` as the server URL.
3. Choose **OAuth**, create the connection, and complete the Trackpac login and consent prompts. The server supports dynamic client registration, so you do not need to enter the Auth0 application's client secret here.
4. Enable Trackpac in a chat and ask **"List my Trackpac devices."**

See [OpenAI's custom MCP server guide](https://developers.openai.com/api/docs/guides/custom-mcp-server) and [authentication requirements](https://developers.openai.com/plugins/build/auth).
