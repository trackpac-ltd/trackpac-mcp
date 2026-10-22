"""Auth0 login and per-request Trackpac credentials for HTTP MCP clients."""

import hashlib
import os
from urllib.parse import urlparse

import httpx2
from fastmcp.server.auth import AccessToken
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.dependencies import get_access_token
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser, BearerAuthBackend
from starlette.authentication import AuthCredentials
from starlette.middleware.authentication import AuthenticationMiddleware


class APIKeyAccessToken(AccessToken):
    """A Trackpac API key validated by the API, rather than an OAuth token."""


class TrackpacAuthBackend(BearerAuthBackend):
    def __init__(self, provider, api_url: str):
        super().__init__(provider)
        self.api_url = api_url

    async def authenticate(self, conn):
        # A failed OAuth credential must not fall back to a different identity.
        if conn.headers.get("authorization"):
            return await super().authenticate(conn)
        api_key = conn.headers.get("x-api-key", "").strip()
        if not api_key:
            return None

        # Check /user/options on every request so revoked keys stop working immediately.
        try:
            async with httpx2.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.api_url}/user/options", headers={"X-API-Key": api_key}
                )
        except httpx2.HTTPError:
            return None
        if response.status_code != 200:
            return None

        identity = "api-key:" + hashlib.sha256(api_key.encode()).hexdigest()
        token = APIKeyAccessToken(
            token=api_key,
            client_id=identity,
            subject=identity,
            scopes=self.token_verifier.required_scopes,
        )
        # Satisfy FastMCP's Bearer-header check after key validation; never forward this marker.
        conn.scope["headers"] = [
            *conn.scope["headers"],
            (b"authorization", b"Bearer trackpac-api-key"),
        ]
        return AuthCredentials(token.scopes), AuthenticatedUser(token)


class TrackpacAuth0Provider(OIDCProxy):
    def __init__(self, *, api_url: str, **kwargs):
        self.api_url = api_url
        super().__init__(**kwargs)

    def get_middleware(self) -> list:
        middleware = super().get_middleware()
        for item in middleware:
            if item.cls is AuthenticationMiddleware:
                item.kwargs["backend"] = TrackpacAuthBackend(self, self.api_url)
        return middleware


class TrackpacAPIAuth(httpx2.Auth):
    """Inject credentials into each outgoing request without changing shared state."""

    def __init__(self, *, oauth_enabled: bool):
        self.oauth_enabled = oauth_enabled

    def auth_flow(self, request):
        # Use the resolved Auth0 token; never forward the incoming MCP session token.
        request.headers.pop("Authorization", None)
        if self.oauth_enabled:
            token = get_access_token()
            if token is None:
                raise RuntimeError("Trackpac OAuth credentials are missing")
            request.headers.pop("X-API-Key", None)
            if isinstance(token, APIKeyAccessToken):
                request.headers["X-API-Key"] = token.token
            else:
                request.headers["Authorization"] = f"Bearer {token.token}"
        yield request


def build_auth(api_url: str) -> TrackpacAuth0Provider | None:
    mode = os.environ.get("TRACKPAC_AUTH", "api-key")
    if mode == "api-key":
        return None
    if mode != "auth0":
        raise ValueError("TRACKPAC_AUTH must be api-key or auth0")
    if os.environ.get("TRACKPAC_API_KEY"):
        raise ValueError("Unset TRACKPAC_API_KEY when TRACKPAC_AUTH=auth0")

    required = (
        "AUTH0_DOMAIN",
        "AUTH0_CLIENT_ID",
        "AUTH0_CLIENT_SECRET",
        "AUTH0_AUDIENCE",
        "MCP_SERVER_URL",
        "OAUTH_JWT_SIGNING_KEY",
        "FASTMCP_HOME",
    )
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise ValueError("Missing OAuth configuration: " + ", ".join(missing))

    domain = os.environ["AUTH0_DOMAIN"].strip()
    if "://" in domain or "/" in domain or not domain:
        raise ValueError("AUTH0_DOMAIN must be a hostname without a scheme or path")
    base_url = os.environ["MCP_SERVER_URL"].rstrip("/")
    parsed = urlparse(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("MCP_SERVER_URL must be an HTTPS origin without a path")
    if len(os.environ["OAUTH_JWT_SIGNING_KEY"]) < 32:
        raise ValueError("OAUTH_JWT_SIGNING_KEY must contain at least 32 characters")

    return TrackpacAuth0Provider(
        api_url=api_url,
        config_url=f"https://{domain}/.well-known/openid-configuration",
        client_id=os.environ["AUTH0_CLIENT_ID"],
        client_secret=os.environ["AUTH0_CLIENT_SECRET"],
        audience=os.environ["AUTH0_AUDIENCE"],
        base_url=base_url,
        jwt_signing_key=os.environ["OAUTH_JWT_SIGNING_KEY"],
        token_endpoint_auth_method="client_secret_post",
        required_scopes=["openid", "profile", "offline_access"],
        # Auth0 uses the API audience; the MCP resource belongs to this proxy.
        forward_resource=False,
    )
