from pet_hospital_mcp.config import settings
from pet_hospital_mcp.server import mcp


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        stateless_http=True,
        json_response=True,
    )