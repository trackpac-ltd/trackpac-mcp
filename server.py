"""
Trackpac MCP server.

Exposes the Trackpac IoT platform API (https://api.trackpac.io) as MCP tools,
built automatically from Trackpac's published OpenAPI spec
(https://api.trackpac.io/openapi.json).

Device-ingest webhook routes (`/ingest/*`, tag "Ingest") are deliberately
excluded — those are one-way endpoints that hardware/LoRaWAN network servers
POST raw sensor payloads to, not something a human or an assistant would ever
call. Legacy base routes (tag "Bases", plus the location engine's base check)
are excluded too; geofences replace them.

Auth
----
This server only ever authenticates with an API key, sent as the
`X-API-Key` header (Trackpac's API also accepts a bearer token via
`Authorization: Bearer <token>`, but that's intentionally not supported
here — API-key-only, by design).

Set this environment variable before running the server:
  - TRACKPAC_API_KEY   (create one from the Trackpac dashboard's API keys
                         page; see README.md if you need to bootstrap the
                         very first one)

Run
---
    python server.py

or via the MCP CLI / a client config, e.g.:
    fastmcp run server.py
"""

from __future__ import annotations

import os
import sys

import httpx2
from fastmcp import FastMCP
from fastmcp.server.providers.openapi.routing import MCPType, RouteMap

TRACKPAC_BASE_URL = "https://api.trackpac.io"
OPENAPI_URL = f"{TRACKPAC_BASE_URL}/openapi.json"

# Tags/path prefixes we never want to expose as callable tools.
EXCLUDED_TAGS = {"Ingest", "Bases"}
# Bases are a legacy feature superseded by geofences, so the location engine's
# base check goes with them even though it's tagged "LoRaWAN Location Engine".
EXCLUDED_PATH_PREFIXES = ("/ingest", "/location-engine/base")
# Webhook receivers outside /ingest are the same shape as an ingest route (an
# external system POSTs to them and they aren't meant to be called directly),
# so any path containing one of these keywords is excluded too.
EXCLUDED_PATH_KEYWORDS = ("webhook", "web-hook")

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def fetch_filtered_spec() -> dict:
    """Fetch Trackpac's live OpenAPI spec and strip the device-ingest routes."""
    resp = httpx2.get(OPENAPI_URL, timeout=30)
    resp.raise_for_status()
    spec = resp.json()

    filtered_paths: dict = {}
    for path, path_item in spec.get("paths", {}).items():
        if path.startswith(EXCLUDED_PATH_PREFIXES) or any(
            keyword in path.lower() for keyword in EXCLUDED_PATH_KEYWORDS
        ):
            continue

        kept_ops: dict = {}
        for key, op in path_item.items():
            if key not in HTTP_METHODS:
                # e.g. "parameters" shared across methods on this path
                kept_ops[key] = op
                continue
            tags = set(op.get("tags", []))
            if tags & EXCLUDED_TAGS:
                continue
            kept_ops[key] = op

        # Only keep the path if it still has at least one real operation.
        if any(k in HTTP_METHODS for k in kept_ops):
            filtered_paths[path] = kept_ops

    spec["paths"] = filtered_paths
    return spec


def build_client() -> httpx2.AsyncClient:
    api_key = os.environ.get("TRACKPAC_API_KEY")

    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    else:
        print(
            "trackpac-mcp: no TRACKPAC_API_KEY set in the environment - "
            "requests to api.trackpac.io will fail auth until one is "
            "configured. (This server is API-key-only; bearer tokens are "
            "not supported.)",
            file=sys.stderr,
        )

    return httpx2.AsyncClient(base_url=TRACKPAC_BASE_URL, headers=headers, timeout=30)


def build_server() -> FastMCP:
    spec = fetch_filtered_spec()
    client = build_client()

    # Expose every remaining operation as a callable tool (rather than letting
    # GETs become MCP "resources"), since a chat assistant driving this
    # reliably needs tool-call semantics with arguments, not resource URIs.
    route_maps = [RouteMap(methods="*", pattern=r".*", mcp_type=MCPType.TOOL)]

    return FastMCP.from_openapi(
        openapi_spec=spec,
        client=client,
        name="Trackpac",
        route_maps=route_maps,
    )


mcp = build_server()


if __name__ == "__main__":
    mcp.run()
