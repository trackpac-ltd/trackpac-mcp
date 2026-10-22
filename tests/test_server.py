import asyncio
import copy
import importlib
import sys

import httpx2
from fastmcp import Client

OK = {"200": {"description": "OK"}}
DEVICE_ID = {
    "name": "device_id",
    "in": "path",
    "required": True,
    "schema": {"type": "integer"},
}

SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "Trackpac", "version": "test"},
    "paths": {
        "/device": {
            "get": {
                "operationId": "list_devices",
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
    },
}


def load_server(monkeypatch, **env):
    for name in ("TRACKPAC_API_KEY", "TRACKPAC_API_URL"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    requested = []

    def fake_get(url, **kwargs):
        requested.append(url)
        return httpx2.Response(
            200, json=copy.deepcopy(SPEC), request=httpx2.Request("GET", url)
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
