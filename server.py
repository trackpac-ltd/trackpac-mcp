"""
Trackpac MCP server: exposes the Trackpac API as MCP tools, generated from its
live OpenAPI spec. Authenticates with an API key only (X-API-Key), never a
bearer token. See README.md for setup.
"""

from __future__ import annotations

import os
import sys

import httpx2
from fastmcp import FastMCP
from fastmcp.server.providers.openapi.components import (
    OpenAPIResource,
    OpenAPIResourceTemplate,
    OpenAPITool,
)
from fastmcp.server.providers.openapi.routing import MCPType, RouteMap
from fastmcp.utilities.openapi.models import HTTPRoute
from mcp.types import ToolAnnotations

TRACKPAC_API_URL = os.environ.get("TRACKPAC_API_URL", "https://api.trackpac.io").rstrip(
    "/"
)
OPENAPI_URL = f"{TRACKPAC_API_URL}/openapi.json"
REQUEST_TIMEOUT = 30

# Ingest and webhook routes are for hardware and network servers to POST to,
# not for people or assistants to call. Bases are legacy; geofences replace
# them, including the location engine's base check.
EXCLUDED_TAGS = {"Ingest", "Bases"}
EXCLUDED_PATH_PREFIXES = ("/ingest", "/location-engine/base")
EXCLUDED_PATH_KEYWORDS = ("webhook", "web-hook")

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def fetch_filtered_spec() -> dict:
    resp = httpx2.get(OPENAPI_URL, timeout=REQUEST_TIMEOUT)
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
            # Non-method keys such as "parameters" apply to every method.
            if key not in HTTP_METHODS:
                kept_ops[key] = op
                continue
            if set(op.get("tags", [])) & EXCLUDED_TAGS:
                continue
            kept_ops[key] = op

        if any(k in HTTP_METHODS for k in kept_ops):
            filtered_paths[path] = kept_ops

    spec["paths"] = filtered_paths
    return spec


def build_client() -> httpx2.AsyncClient:
    api_key = os.environ.get("TRACKPAC_API_KEY")
    if not api_key:
        print(
            "trackpac-mcp: no TRACKPAC_API_KEY set, so every request must carry "
            "the caller's own X-API-Key header (hosted HTTP mode).",
            file=sys.stderr,
        )

    headers = {"X-API-Key": api_key} if api_key else {}
    return httpx2.AsyncClient(
        base_url=TRACKPAC_API_URL, headers=headers, timeout=REQUEST_TIMEOUT
    )


def annotate(
    route: HTTPRoute,
    component: OpenAPITool | OpenAPIResource | OpenAPIResourceTemplate,
) -> None:
    if not isinstance(component, OpenAPITool):
        return
    # v2-api keeps state-changing GETs out of the public schema, so GET means read.
    method = route.method.upper()
    if method == "GET":
        component.annotations = ToolAnnotations(read_only_hint=True)
    elif method == "DELETE":
        component.annotations = ToolAnnotations(destructive_hint=True)


def build_server() -> FastMCP:
    # Assistants call tools far more reliably than they read resources, so GETs
    # become tools too.
    route_maps = [RouteMap(methods="*", pattern=r".*", mcp_type=MCPType.TOOL)]

    return FastMCP.from_openapi(
        openapi_spec=fetch_filtered_spec(),
        client=build_client(),
        name="Trackpac",
        route_maps=route_maps,
        mcp_component_fn=annotate,
    )


mcp = build_server()


if __name__ == "__main__":
    mcp.run()
