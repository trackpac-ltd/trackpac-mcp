"""Expose the Trackpac API as MCP tools using its live OpenAPI spec."""

import base64
import os
import sys
from pathlib import Path

import httpx2
from fastmcp import FastMCP
from fastmcp.server.providers.openapi.components import (
    OpenAPIResource,
    OpenAPIResourceTemplate,
    OpenAPITool,
)
from fastmcp.server.providers.openapi.routing import MCPType, RouteMap
from fastmcp.utilities.openapi.models import HTTPRoute
from mcp.types import Icon, ToolAnnotations

from trackpac_auth import TrackpacAPIAuth, build_auth

TRACKPAC_API_URL = os.environ.get("TRACKPAC_API_URL", "https://api.trackpac.io").rstrip(
    "/"
)
OPENAPI_URL = f"{TRACKPAC_API_URL}/openapi.json"
REQUEST_TIMEOUT = 30
ICON_PATH = Path(__file__).parent / "assets" / "trackpac-icon.png"
# Branding shown on the OAuth consent page and in MCP clients; whitelabels override these.
SERVER_NAME = os.environ.get("MCP_SERVER_NAME", "Trackpac")
WEBSITE_URL = os.environ.get("MCP_WEBSITE_URL", "https://trackpac.io")
ICON_URL = os.environ.get("MCP_ICON_URL", "")

# Exclude hardware webhooks and legacy bases; use geofences instead of bases.
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


def build_client(*, oauth_enabled: bool = False) -> httpx2.AsyncClient:
    api_key = os.environ.get("TRACKPAC_API_KEY")
    if not api_key and not oauth_enabled:
        print(
            "trackpac-mcp: no TRACKPAC_API_KEY set, so every request must carry "
            "the caller's own X-API-Key header (hosted HTTP mode).",
            file=sys.stderr,
        )

    headers = {"X-API-Key": api_key} if api_key else {}
    return httpx2.AsyncClient(
        base_url=TRACKPAC_API_URL,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        auth=TrackpacAPIAuth(oauth_enabled=oauth_enabled),
    )


def annotate(
    route: HTTPRoute,
    component: OpenAPITool | OpenAPIResource | OpenAPIResourceTemplate,
) -> None:
    if not isinstance(component, OpenAPITool):
        return
    # The API keeps state-changing GETs out of its public schema, so GET always means read.
    method = route.method.upper()
    if method == "GET":
        component.annotations = ToolAnnotations(read_only_hint=True)
    elif method == "DELETE":
        component.annotations = ToolAnnotations(destructive_hint=True)


def build_icon() -> Icon:
    if not ICON_URL:
        icon = base64.b64encode(ICON_PATH.read_bytes()).decode("ascii")
        return Icon(
            src=f"data:image/png;base64,{icon}",
            mime_type="image/png",
            sizes=["512x512"],
        )
    # The consent page CSP only allows https: and data: images.
    if not ICON_URL.startswith("https://"):
        raise ValueError("MCP_ICON_URL must be an https:// URL")
    return Icon(src=ICON_URL)


def build_server() -> FastMCP:
    auth = build_auth(TRACKPAC_API_URL)
    # GETs become tools because assistants use tools more reliably than resources.
    route_maps = [RouteMap(methods="*", pattern=r".*", mcp_type=MCPType.TOOL)]

    return FastMCP.from_openapi(
        openapi_spec=fetch_filtered_spec(),
        client=build_client(oauth_enabled=auth is not None),
        name=SERVER_NAME,
        website_url=WEBSITE_URL,
        icons=[build_icon()],
        auth=auth,
        route_maps=route_maps,
        mcp_component_fn=annotate,
    )


mcp = build_server()


if __name__ == "__main__":
    mcp.run()
