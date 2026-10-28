import asyncio
import base64
import copy
import hashlib
import json
import re
import time
from urllib.parse import parse_qs, urlparse

import fastmcp
import httpx2
import pytest
from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken
from fastmcp.server.auth.oidc_proxy import _clear_oidc_configuration_cache
from fastmcp.server.auth.providers.jwt import JWTVerifier
from joserfc import jwt
from joserfc.jwk import RSAKey
from mcp.types import Implementation
from starlette.requests import HTTPConnection
from starlette.testclient import TestClient

import trackpac_auth
from trackpac_auth import (
    APIKeyAccessToken,
    TrackpacAPIAuth,
    TrackpacAuthBackend,
    build_auth,
)

OAUTH_ENV = {
    "TRACKPAC_AUTH": "auth0",
    "AUTH0_DOMAIN": "login.example.com",
    "AUTH0_CLIENT_ID": "trackpac-mcp-app",
    "AUTH0_CLIENT_SECRET": "test-client-secret",
    "AUTH0_AUDIENCE": "https://api.trackpac.io",
    "MCP_SERVER_URL": "https://mcp.trackpac.io",
    "OAUTH_JWT_SIGNING_KEY": "test-signing-key-with-at-least-32-characters",
    "FASTMCP_HOME": "/unused-in-tests",
}
OIDC = {
    "issuer": "https://login.example.com/",
    "authorization_endpoint": "https://login.example.com/authorize",
    "token_endpoint": "https://login.example.com/oauth/token",
    "jwks_uri": "https://login.example.com/.well-known/jwks.json",
    "response_types_supported": ["code"],
    "subject_types_supported": ["public"],
    "id_token_signing_alg_values_supported": ["RS256"],
    "scopes_supported": ["openid", "profile", "offline_access"],
}


@pytest.fixture
def oauth_config(monkeypatch, tmp_path):
    for key in (*OAUTH_ENV, "TRACKPAC_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in OAUTH_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(fastmcp.settings, "home", tmp_path)
    _clear_oidc_configuration_cache()

    def discovery(url, **kwargs):
        assert url == "https://login.example.com/.well-known/openid-configuration"
        return httpx2.Response(
            200, json=copy.deepcopy(OIDC), request=httpx2.Request("GET", url)
        )

    monkeypatch.setattr(httpx2, "get", discovery)
    return build_auth("https://api.trackpac.io")


def test_oauth_discovery_and_missing_credentials(oauth_config):
    app = FastMCP("Trackpac", auth=oauth_config).http_app()
    with TestClient(app) as client:
        metadata = client.get("/.well-known/oauth-authorization-server")
        assert metadata.status_code == 200
        assert metadata.json()["issuer"].rstrip("/") == "https://mcp.trackpac.io"
        resource = client.get("/.well-known/oauth-protected-resource/mcp")
        assert resource.status_code == 200
        assert resource.json()["resource"] == "https://mcp.trackpac.io/mcp"
        for headers in (
            {},
            {"Authorization": "Bearer invalid"},
            {"Authorization": "Bearer trackpac-api-key"},
        ):
            response = client.post("/mcp", headers=headers, json={})
            assert response.status_code == 401
            assert "resource_metadata=" in response.headers["www-authenticate"]


def test_auth0_authorization_uses_api_audience_not_mcp_resource(oauth_config):
    url = oauth_config._build_upstream_authorize_url(
        "transaction-id",
        {
            "scopes": ["openid", "profile", "offline_access"],
            "resource": "https://mcp.trackpac.io/mcp",
        },
    )
    query = parse_qs(urlparse(url).query)
    assert query["audience"] == ["https://api.trackpac.io"]
    assert query["redirect_uri"] == ["https://mcp.trackpac.io/auth/callback"]
    assert query["client_id"] == ["trackpac-mcp-app"]
    assert "resource" not in query
    assert "offline_access" in query["scope"][0]


def test_api_key_backend_validates_each_request_and_rejects_revoked_key(
    oauth_config, monkeypatch
):
    requests = []
    statuses = iter([200, 401])

    async def get(client, url, *, headers):
        requests.append((url, headers))
        return httpx2.Response(next(statuses))

    monkeypatch.setattr(httpx2.AsyncClient, "get", get)
    backend = TrackpacAuthBackend(oauth_config, "https://api.trackpac.io")
    conn = HTTPConnection({"type": "http", "headers": [(b"x-api-key", b"alice-key")]})

    async def run():
        first = await backend.authenticate(conn)
        assert first is not None
        assert isinstance(first[1].access_token, APIKeyAccessToken)
        assert first[1].access_token.token == "alice-key"
        assert "alice-key" not in first[1].identity
        assert await backend.authenticate(conn) is None

    asyncio.run(run())
    assert (
        requests
        == [("https://api.trackpac.io/user/options", {"X-API-Key": "alice-key"})] * 2
    )


def test_invalid_bearer_does_not_fall_back_to_api_key(oauth_config, monkeypatch):
    async def fail_if_called(*args, **kwargs):
        pytest.fail("An API key must not override an invalid OAuth credential")

    monkeypatch.setattr(httpx2.AsyncClient, "get", fail_if_called)
    backend = TrackpacAuthBackend(oauth_config, "https://api.trackpac.io")
    conn = HTTPConnection(
        {
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer invalid"),
                (b"x-api-key", b"alice-key"),
            ],
        }
    )
    assert asyncio.run(backend.authenticate(conn)) is None


def test_outgoing_credentials_are_isolated_and_oauth_replaces_untrusted_headers(
    monkeypatch,
):
    current = None
    monkeypatch.setattr(trackpac_auth, "get_access_token", lambda: current)
    observed = []

    def respond(request):
        observed.append(dict(request.headers))
        return httpx2.Response(200, json={})

    async def run():
        nonlocal current
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(respond),
            auth=TrackpacAPIAuth(oauth_enabled=True),
        ) as client:
            current = AccessToken(
                token="alice-upstream-token", client_id="alice", scopes=[]
            )
            await client.get(
                "https://api.trackpac.io/device",
                headers={"Authorization": "Bearer mcp-session", "X-API-Key": "wrong"},
            )
            current = APIKeyAccessToken(token="bob-api-key", client_id="bob", scopes=[])
            await client.get("https://api.trackpac.io/device")
            current = AccessToken(
                token="carol-upstream-token", client_id="carol", scopes=[]
            )
            await client.get("https://api.trackpac.io/device")
            current = None
            with pytest.raises(RuntimeError, match="credentials are missing"):
                await client.get("https://api.trackpac.io/device")

    asyncio.run(run())
    assert observed[0]["authorization"] == "Bearer alice-upstream-token"
    assert "x-api-key" not in observed[0]
    assert observed[1]["x-api-key"] == "bob-api-key"
    assert "authorization" not in observed[1]
    assert observed[2]["authorization"] == "Bearer carol-upstream-token"
    assert "x-api-key" not in observed[2]


def test_api_key_mode_never_forwards_bearer_tokens():
    request = httpx2.Request(
        "GET",
        "https://api.trackpac.io/device",
        headers={"Authorization": "Bearer unverified", "X-API-Key": "alice-key"},
    )
    authenticated = next(TrackpacAPIAuth(oauth_enabled=False).auth_flow(request))
    assert "authorization" not in authenticated.headers
    assert authenticated.headers["X-API-Key"] == "alice-key"


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("TRACKPAC_AUTH", "typo", "TRACKPAC_AUTH must be"),
        ("AUTH0_CLIENT_SECRET", "", "Missing OAuth configuration"),
        ("TRACKPAC_API_KEY", "shared-key", "Unset TRACKPAC_API_KEY"),
        ("AUTH0_DOMAIN", "https://login.example.com/", "must be a hostname"),
        ("MCP_SERVER_URL", "http://mcp.trackpac.io", "must be an HTTPS origin"),
        ("MCP_SERVER_URL", "https://mcp.trackpac.io/mcp", "without a path"),
        ("OAUTH_JWT_SIGNING_KEY", "short", "at least 32 characters"),
    ],
)
def test_invalid_oauth_configuration_fails_closed(
    oauth_config, monkeypatch, name, value, message
):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=message):
        build_auth("https://api.trackpac.io")


def test_oauth_login_refresh_and_restart_keep_upstream_tokens_private(
    oauth_config, monkeypatch
):
    key = RSAKey.generate_key(2048)
    now = int(time.time())
    scopes = "openid profile offline_access"

    def upstream_token(subject):
        return jwt.encode(
            {"alg": "RS256"},
            {
                "iss": OIDC["issuer"],
                "aud": OAUTH_ENV["AUTH0_AUDIENCE"],
                "sub": subject,
                "azp": OAUTH_ENV["AUTH0_CLIENT_ID"],
                "scope": scopes,
                "iat": now,
                "exp": now + 3600,
            },
            key,
        )

    alice_token = upstream_token("auth0|alice")
    refreshed_token = upstream_token("auth0|alice")
    upstream_grants = []

    async def token_endpoint(client, url, *, data, headers=None):
        assert str(url) == OIDC["token_endpoint"]
        assert data["client_id"] == OAUTH_ENV["AUTH0_CLIENT_ID"]
        assert data["client_secret"] == OAUTH_ENV["AUTH0_CLIENT_SECRET"]
        assert "Authorization" not in (headers or {})
        upstream_grants.append(data)
        is_refresh = data["grant_type"] == "refresh_token"
        if is_refresh:
            assert data["refresh_token"] == "auth0-private-refresh"
        return httpx2.Response(
            200,
            json={
                "access_token": refreshed_token if is_refresh else alice_token,
                "refresh_token": "auth0-private-refresh",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": scopes,
            },
            request=httpx2.Request("POST", url),
        )

    monkeypatch.setattr(httpx2.AsyncClient, "post", token_endpoint)
    observed = []

    def api(request):
        observed.append(dict(request.headers))
        return httpx2.Response(200, json={"ok": True})

    def make_app(provider):
        provider._token_validator = JWTVerifier(
            public_key=key.as_pem(),
            issuer=OIDC["issuer"],
            audience=OAUTH_ENV["AUTH0_AUDIENCE"],
            required_scopes=scopes.split(),
        )
        mcp = FastMCP.from_openapi(
            openapi_spec={
                "openapi": "3.1.0",
                "info": {"title": "Trackpac", "version": "test"},
                "paths": {
                    "/device": {
                        "get": {
                            "operationId": "list_devices",
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            },
            client=httpx2.AsyncClient(
                base_url="https://api.trackpac.io",
                transport=httpx2.MockTransport(api),
                auth=TrackpacAPIAuth(oauth_enabled=True),
            ),
            auth=provider,
        )
        return mcp.http_app()

    verifier = "test-code-verifier-with-at-least-43-characters-long"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    challenge = challenge.decode().rstrip("=")
    redirect_uri = "http://127.0.0.1:12345/callback"
    base_url = OAUTH_ENV["MCP_SERVER_URL"]

    with TestClient(make_app(oauth_config), base_url=base_url) as client:
        registered = client.post(
            "/register",
            json={
                "client_name": "Trackpac test client",
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
                "scope": scopes,
            },
        )
        assert registered.status_code == 201, registered.text
        client_id = registered.json()["client_id"]
        authorization = client.get(
            "/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scopes,
                "state": "test-client-state",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": base_url + "/mcp",
            },
            follow_redirects=False,
        )
        assert authorization.status_code in (302, 303), authorization.text
        consent_url = authorization.headers["location"]
        consent = client.get(consent_url)
        assert consent.status_code == 200, consent.text
        fields = dict(re.findall(r'name="([^"]+)" value="([^"]+)"', consent.text))
        approved = client.post(
            consent_url,
            data={**fields, "action": "approve"},
            follow_redirects=False,
        )
        assert approved.status_code in (302, 303), approved.text
        auth0_query = parse_qs(urlparse(approved.headers["location"]).query)
        assert auth0_query["audience"] == [OAUTH_ENV["AUTH0_AUDIENCE"]]
        callback = client.get(
            "/auth/callback",
            params={"code": "auth0-one-time-code", "state": auth0_query["state"][0]},
            follow_redirects=False,
        )
        assert callback.status_code in (302, 303), callback.text
        code = parse_qs(urlparse(callback.headers["location"]).query)["code"][0]
        token_response = client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code": code,
                "code_verifier": verifier,
                "resource": base_url + "/mcp",
            },
        )
        assert token_response.status_code == 200, token_response.text
        tokens = token_response.json()
        assert tokens["access_token"] != alice_token
        assert tokens["refresh_token"] != "auth0-private-refresh"
        assert "auth0-private-refresh" not in token_response.text
        # A raw Auth0 API token is not an MCP session credential.
        rejected = client.post(
            "/mcp", headers={"Authorization": f"Bearer {alice_token}"}, json={}
        )
        assert rejected.status_code == 401
        refresh = client.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert refresh.status_code == 200, refresh.text
        tokens = refresh.json()

    # Reload provider and storage as a new process would, with the same secrets.
    restarted = build_auth("https://api.trackpac.io")
    with TestClient(make_app(restarted), base_url=base_url) as client:
        headers = {
            "Authorization": "Bearer " + tokens["access_token"],
            "Accept": "application/json, text/event-stream",
        }
        initialized = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        assert initialized.status_code == 200, initialized.text
        headers["mcp-session-id"] = initialized.headers["mcp-session-id"]
        headers["X-API-Key"] = "must-not-reach-the-api"
        called = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "list_devices", "arguments": {}},
            },
        )
        assert called.status_code == 200, called.text
        data = next(
            line[6:] for line in called.text.splitlines() if line.startswith("data: ")
        )
        assert not json.loads(data)["result"].get("isError"), called.text
        assert tokens["access_token"] not in called.text

    assert observed[-1]["authorization"] == f"Bearer {refreshed_token}"
    assert "x-api-key" not in observed[-1]
    assert [grant["grant_type"] for grant in upstream_grants] == [
        "authorization_code",
        "refresh_token",
    ]
    stored = b"".join(
        path.read_bytes() for path in fastmcp.settings.home.rglob("*") if path.is_file()
    )
    assert b"auth0-private-refresh" not in stored
    assert alice_token.encode() not in stored


def test_api_key_http_clients_keep_existing_setup_and_cannot_share_sessions(
    oauth_config, monkeypatch
):
    async def get(client, url, *, headers):
        assert url == "https://api.trackpac.io/user/options"
        return httpx2.Response(200 if headers["X-API-Key"] in {"alice", "bob"} else 401)

    monkeypatch.setattr(httpx2.AsyncClient, "get", get)
    app = FastMCP("Trackpac", auth=oauth_config).http_app()
    with TestClient(app, base_url=OAUTH_ENV["MCP_SERVER_URL"]) as client:
        headers = {
            "X-API-Key": "alice",
            "Accept": "application/json, text/event-stream",
        }
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        }
        initialized = client.post("/mcp", headers=headers, json=message)
        assert initialized.status_code == 200, initialized.text
        headers["mcp-session-id"] = initialized.headers["mcp-session-id"]
        ping = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        assert client.post("/mcp", headers=headers, json=ping).status_code == 200
        headers["X-API-Key"] = "bob"
        assert client.post("/mcp", headers=headers, json=ping).status_code == 404
        headers["X-API-Key"] = "revoked"
        assert client.post("/mcp", headers=headers, json=ping).status_code == 401


def test_api_key_backend_rejects_unavailable_api(oauth_config, monkeypatch):
    async def get(*args, **kwargs):
        raise httpx2.ConnectError("Unavailable")

    monkeypatch.setattr(httpx2.AsyncClient, "get", get)
    conn = HTTPConnection({"type": "http", "headers": [(b"x-api-key", b"alice")]})
    backend = TrackpacAuthBackend(oauth_config, "https://api.trackpac.io")
    assert asyncio.run(backend.authenticate(conn)) is None


@pytest.mark.parametrize(
    ("name", "header"),
    [
        ("claude-ai", "claude-ai"),
        ("Café 🤖", "Caf"),
        ("a" * 39 + " cut", "a" * 39),
        ("evil\r\nX-API-Key: stolen", "evilX-API-Key: stolen"),
        ("🤖", None),
    ],
)
def test_tool_calls_tell_the_api_which_mcp_client_made_them(name, header):
    observed = []

    def respond(request):
        observed.append(dict(request.headers))
        return httpx2.Response(200, json={})

    spec = {
        "openapi": "3.1.0",
        "info": {"title": "t", "version": "1"},
        "paths": {"/device": {"get": {"operationId": "list_devices", "responses": {}}}},
    }
    api = httpx2.AsyncClient(
        base_url="https://api.trackpac.io",
        transport=httpx2.MockTransport(respond),
        auth=TrackpacAPIAuth(oauth_enabled=False),
    )
    server = FastMCP.from_openapi(openapi_spec=spec, client=api)

    async def run():
        async with fastmcp.Client(
            server, client_info=Implementation(name=name, version="1")
        ) as client:
            await client.call_tool("list_devices", {})

    asyncio.run(run())
    assert observed[0].get("x-mcp-client") == header
