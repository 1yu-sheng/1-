import os
import asyncio
import httpx
from mcp.server.mcpserver import MCPServer

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = val.strip('"').strip("'")

load_env()

ANYTHINGLLM_API_KEY = os.environ.get("ANYTHINGLLM_API_KEY", "")
ANYTHINGLLM_BASE_URL = os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001")
WORKSPACE_SLUG = os.environ.get("ANYTHINGLLM_WORKSPACE_SLUG", "531cfcc3-6220-455e-8190-dde1e78e4f44")

server = MCPServer(
    name="anythingllm-mcp",
    title="AnythingLLM MCP Server",
    description="MCP server for interacting with AnythingLLM workspaces",
    instructions="Provides tools to chat with AnythingLLM workspaces.",
    version="0.1.0",
)

@server.tool()
async def chat_with_workspace(message: str) -> str:
    """Send a message to the AnythingLLM workspace and get an AI response."""
    if not ANYTHINGLLM_API_KEY:
        return "Error: ANYTHINGLLM_API_KEY environment variable not set."
    url = f"{ANYTHINGLLM_BASE_URL}/api/v1/workspace/{WORKSPACE_SLUG}/chat"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            json={"message": message, "mode": "chat"},
            headers={"Authorization": f"Bearer {ANYTHINGLLM_API_KEY}", "Content-Type": "application/json"},
        )
    if resp.status_code != 200:
        return f"Error: {resp.text}"
    data = resp.json()
    if data.get("error"):
        return f"Error: {data['error']}"
    return str(data)

async def main():
    await server.run_streamable_http_async(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    asyncio.run(main())
