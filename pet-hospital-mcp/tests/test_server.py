import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient
from starlette.responses import JSONResponse


@pytest.mark.asyncio
async def test_server_imports():
    from pet_hospital_mcp.server import mcp, app
    assert mcp is not None
    assert app is not None


@pytest.mark.asyncio
async def test_health_endpoint():
    from pet_hospital_mcp.server import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_mcp_tool_list_pets_registered():
    from pet_hospital_mcp.server import mcp
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "list_pets" in tool_names


@pytest.mark.asyncio
async def test_mcp_tool_schema():
    from pet_hospital_mcp.server import mcp
    tools = await mcp.list_tools()
    tool = next(t for t in tools if t.name == "list_pets")
    schema = tool.input_schema
    assert "properties" in schema
    assert "species" in schema["properties"]
    assert "status" in schema["properties"]
    assert "page" in schema["properties"]
    assert "pageSize" in schema["properties"]