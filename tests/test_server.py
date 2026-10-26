import asyncio
import copy
import importlib
import sys

import httpx2
import pytest
from fastmcp import Client

OK = {"200": {"description": "OK"}}
DEVICE_ID = {
    "name": "device_id",
    "in": "path",
    "required": True,
    "description": "Internal numeric device ID from list_devices.",
    "schema": {"type": "integer"},
}

SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "Trackpac", "version": "test"},
    "paths": {
        "/device": {
            "get": {
                "operationId": "list_devices",
                "summary": "List devices",
                "description": "Lists devices available to the current user.",
                "tags": ["Devices"],
                "responses": OK,
            },
        },
        "/device/{device_id}": {
            "parameters": [DEVICE_ID],
            "put": {
                "operationId": "update_device",
                "tags": ["Devices"],
                "responses": OK,
            },
            "delete": {
                "operationId": "delete_device",
                "tags": ["Devices"],
                "responses": OK,
            },
        },
        "/ingest/acme/tracker": {
            "post": {"operationId": "ingest_acme", "tags": ["Ingest"], "responses": OK},
        },
        "/billing/stripe-web-hook": {
            "post": {
                "operationId": "stripe_webhook",
                "tags": ["Billing"],
                "responses": OK,
            },
        },
        "/base": {
            "get": {"operationId": "list_bases", "tags": ["Bases"], "responses": OK},
        },
        "/location-engine/base/check": {
            "post": {
                "operationId": "check_base",
                "tags": ["LoRaWAN Location Engine"],
                "responses": OK,
            },
        },
        "/mixed": {
            "get": {"operationId": "mixed_ingest", "tags": ["Ingest"], "responses": OK},
            "post": {
                "operationId": "create_mixed",
                "tags": ["Devices"],
                "responses": OK,
            },
        },
        "/action/assign": {
            "post": {
                "operationId": "assign_action",
                "summary": "Assign actions",
                "description": "Assigns the selected actions to a device.",
                "tags": ["Actions"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["device_id", "actions"],
                                "properties": {
                                    "device_id": {
                                        "type": "integer",
                                        "description": "Device ID from list_devices.",
                                    },
                                    "actions": {
                                        "type": "array",
                                        "description": "Action IDs from list_actions.",
                                        "items": {
                                            "type": "object",
                                            "required": ["id"],
                                            "properties": {"id": {"type": "integer"}},
                                        },
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": OK,
            },
        },
    },
}


def load_server(monkeypatch, spec=SPEC, **env):
    for name in (
        "TRACKPAC_API_KEY",
        "TRACKPAC_API_URL",
        "MCP_SERVER_NAME",
        "MCP_WEBSITE_URL",
        "MCP_ICON_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    requested = []

    def fake_get(url, **kwargs):
        requested.append(url)
        return httpx2.Response(
            200, json=copy.deepcopy(spec), request=httpx2.Request("GET", url)
        )

    monkeypatch.setattr(httpx2, "get", fake_get)
    sys.modules.pop("server", None)
    return importlib.import_module("server"), requested


def list_tools(mcp):
    async def run():
        async with Client(mcp) as client:
            return {tool.name: tool for tool in await client.list_tools()}

    return asyncio.run(run())


def test_only_callable_routes_become_tools(monkeypatch):
    server, _ = load_server(monkeypatch)

    assert set(list_tools(server.mcp)) == {
        "list_devices",
        "update_device",
        "delete_device",
        "create_mixed",
        "assign_action",
    }


def test_path_level_parameters_are_kept(monkeypatch):
    server, _ = load_server(monkeypatch)

    tool = list_tools(server.mcp)["delete_device"]

    assert "device_id" in tool.input_schema["properties"]


def test_tools_are_annotated_by_http_method(monkeypatch):
    server, _ = load_server(monkeypatch)

    tools = list_tools(server.mcp)

    assert tools["list_devices"].annotations.read_only_hint is True
    assert tools["delete_device"].annotations.destructive_hint is True
    assert tools["update_device"].annotations is None


def test_api_url_can_be_overridden(monkeypatch):
    server, requested = load_server(
        monkeypatch, TRACKPAC_API_URL="http://localhost:8000/"
    )

    assert requested == ["http://localhost:8000/openapi.json"]
    assert server.build_client().base_url == "http://localhost:8000"


def test_api_key_header_is_only_sent_when_configured(monkeypatch):
    server, _ = load_server(monkeypatch, TRACKPAC_API_KEY="secret")
    assert server.build_client().headers["X-API-Key"] == "secret"

    server, _ = load_server(monkeypatch)
    assert "X-API-Key" not in server.build_client().headers


def test_branding_defaults_to_trackpac(monkeypatch):
    server, _ = load_server(monkeypatch)

    assert server.mcp.name == "Trackpac"
    assert server.mcp.website_url == "https://trackpac.io"
    assert server.mcp.icons[0].src.startswith("data:image/png;base64,")


def test_branding_can_be_overridden(monkeypatch):
    server, _ = load_server(
        monkeypatch,
        MCP_SERVER_NAME="Connect IoT",
        MCP_WEBSITE_URL="https://connect-iot.eu",
        MCP_ICON_URL="https://connect-iot.eu/logo.png",
    )

    assert server.mcp.name == "Connect IoT"
    assert server.mcp.website_url == "https://connect-iot.eu"
    assert server.mcp.icons[0].src == "https://connect-iot.eu/logo.png"


def test_icon_url_must_be_https(monkeypatch):
    with pytest.raises(ValueError, match="MCP_ICON_URL"):
        load_server(monkeypatch, MCP_ICON_URL="http://connect-iot.eu/logo.png")


def test_openapi_metadata_reaches_generated_tools(monkeypatch):
    server, _ = load_server(monkeypatch)
    tools = list_tools(server.mcp)

    assert (
        tools["list_devices"].description
        == "Lists devices available to the current user."
    )
    assert (
        tools["delete_device"].input_schema["properties"]["device_id"]["description"]
        == "Internal numeric device ID from list_devices."
    )
    assign = tools["assign_action"]
    assert assign.description == "Assigns the selected actions to a device."
    actions = assign.input_schema["properties"]["actions"]
    assert actions["description"] == "Action IDs from list_actions."
    assert actions["items"]["properties"]["id"]["type"] == "integer"
