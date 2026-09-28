from __future__ import annotations

import asyncio
import json
import socket
import threading
from dataclasses import dataclass, field

import httpx2
import pytest
import uvicorn
from mcp.client.client import Client
from mcp.client.streamable_http import streamable_http_client

from pet_hospital_mcp import server as server_mod
from pet_hospital_mcp.errors import PetItem, PetListResponse
from pet_hospital_mcp.rest_client import PetHospitalClient
from pet_hospital_mcp.server import create_app


class _FakePetClient:
    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        pass

    async def __aenter__(self) -> _FakePetClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def list_pets(self, **kwargs: object) -> PetListResponse:
        return PetListResponse(
            items=[
                PetItem(
                    id="PET-XYZ",
                    name="测试宠物",
                    species="犬",
                    breed="金毛",
                    gender="公",
                    ageMonths=24,
                    ownerName="张三",
                    disease="肠胃炎",
                    doctor="李医生",
                    status="待就诊",
                    totalCost=1200.0,
                )
            ],
            total=1,
            page=int(kwargs.get("page", 1)),
            pageSize=int(kwargs.get("pageSize", 10)),
            totalPages=1,
            totalCost=1200.0,
        )


class _RecordingTransport(httpx2.AsyncBaseTransport):
    def __init__(self, base: httpx2.AsyncBaseTransport, sink: list[dict[str, str]]):
        self._base = base
        self._sink = sink

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        self._sink.append(
            {
                "method": request.method,
                "path": request.url.path,
                "body": request.content.decode("utf-8", errors="replace"),
            }
        )
        return await self._base.handle_async_request(request)


@dataclass
class _Hub:
    port: int
    records: list[dict[str, str]] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp"

    def async_client(self) -> httpx2.AsyncClient:
        transport = _RecordingTransport(httpx2.AsyncHTTPTransport(), self.records)
        return httpx2.AsyncClient(transport=transport)

    def connect(self) -> Client:
        hx = self.async_client()
        return Client(streamable_http_client(self.url, http_client=hx))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def hub():
    port = _free_port()
    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(200):
            if server.started:
                break
            await asyncio.sleep(0.02)
        if not server.started:
            raise RuntimeError("uvicorn failed to start")
        yield _Hub(port=port)
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.asyncio
async def test_stateless_http_discover_uses_modern_protocol_no_initialize(hub):
    async with hub.connect() as client:
        await client.list_tools()

    assert hub.records, "no HTTP requests were made"
    methods = [r["body"] for r in hub.records]
    assert any('"server/discover"' in b for b in methods)
    assert any('"tools/list"' in b for b in methods)
    assert any("2026-07-28" in b for b in methods)
    for body in methods:
        assert '"initialize"' not in body
        assert '"initialized"' not in body


@pytest.mark.asyncio
async def test_stateless_http_tools_list_registers_list_pets(hub):
    async with hub.connect() as client:
        result = await client.list_tools()
    names = [tool.name for tool in result.tools]
    assert "list_pets" in names


@pytest.mark.asyncio
async def test_stateless_http_call_tool_error_maps_to_structured_error(hub):
    from mcp.shared.exceptions import MCPError

    async with hub.connect() as client:
        with pytest.raises(MCPError) as exc_info:
            await client.call_tool("list_pets", {"species": "invalid"})

    error = exc_info.value.data["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "Invalid input" in error["message"]
    assert "species" in json.dumps(error["details"])
    assert exc_info.value.code == -32001


class _UnavailablePetClient(PetHospitalClient):
    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        super().__init__(base_url, timeout=2.0, max_retries=1)


@pytest.mark.asyncio
async def test_stateless_http_call_tool_backend_unavailable(hub, monkeypatch):
    from mcp.shared.exceptions import MCPError

    monkeypatch.setattr(server_mod, "PetHospitalClient", _UnavailablePetClient)
    monkeypatch.setattr(server_mod.settings, "PET_HOSPITAL_BASE_URL", "http://127.0.0.1:1")

    async with hub.connect() as client:
        with pytest.raises(MCPError) as exc_info:
            await client.call_tool("list_pets", {"page": 1, "pageSize": 10})

    error = exc_info.value.data["error"]
    assert error["code"] in {"BACKEND_UNAVAILABLE", "BACKEND_TIMEOUT"}
    assert exc_info.value.code in {-32003, -32002}


@pytest.mark.asyncio
async def test_stateless_http_call_tool_success(hub, monkeypatch):
    monkeypatch.setattr(server_mod, "PetHospitalClient", _FakePetClient)

    async with hub.connect() as client:
        result = await client.call_tool(
            "list_pets", {"species": "犬", "page": 1, "pageSize": 10}
        )

    assert result.is_error is False
    assert result.structured_content["total"] == 1
    items = result.structured_content["items"]
    assert items[0]["id"] == "PET-XYZ"
    assert items[0]["species"] == "犬"
    assert any('"tools/call"' in r["body"] for r in hub.records)
    call_body = next(r["body"] for r in hub.records if '"tools/call"' in r["body"])
    assert '"name":"list_pets"' in call_body


@pytest.mark.asyncio
async def test_stateless_http_no_session_id_issued(hub):
    import httpx

    url = f"http://127.0.0.1:{hub.port}/mcp"
    async with httpx.AsyncClient() as c:
        async with c.stream(
            "GET", url, headers={"Accept": "application/json, text/event-stream"}
        ) as r:
            assert r.status_code == 200
            assert "mcp-session-id" not in r.headers
            await r.aclose()