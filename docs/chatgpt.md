# ChatGPT

[← Back to client setup](../README.md#client-setup)

**The hosted server does not support direct ChatGPT connections yet.** ChatGPT cannot send a custom `X-API-Key` header. Supporting authenticated per-user access requires OAuth on the MCP server or an OAuth gateway that maps each signed-in user to their Trackpac credentials. Selecting "No authentication" does not give ChatGPT access to your Trackpac account.

See [OpenAI's authentication requirements](https://developers.openai.com/plugins/build/auth).
