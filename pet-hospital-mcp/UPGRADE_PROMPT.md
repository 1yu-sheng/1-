# Upgrade Prompt

## 从 SDK 1.x 迁移到 SDK 2.x

### 主要变更

1. **不再使用 `FastMCP`**：本项目使用 `MCPServer`，不使用 `mcp.server.fastmcp.FastMCP`
2. **无状态 Streamable HTTP**：不实现 `initialize`、`Mcp-Session-Id`、会话存储、会话过期、`max_sessions` 或有状态 SSE 恢复机制
3. **协议版本**：使用 `2026-07-28` 规范
4. **工具调用失败**：不使用 `CallToolResult.isError`；工具直接抛异常，失败时抛 `MCPError`（携带结构化 `{error:{code,message,details}}`，通过 JSON-RPC error 的 `data` 字段传输）
5. **`server/discover`**：由 `MCPServer` 自动处理，客户端通过此端点发现支持版本和能力
6. **`@mcp.tool()` 装饰器**：直接装饰异步函数，类型提示自动生成 JSON Schema
7. **`mcp.run()`**：同步调用，传入 `transport` 参数启动服务

### 关键 API 对照

| SDK 1.x | SDK 2.x |
|---------|---------|
| `FastMCP` | `MCPServer` |
| `@app.tool()` (FastMCP) | `@mcp.tool()` (MCPServer) |
| `CallToolResult.isError` | 异常抛出 / 返回错误结构 |
| `initialize` 握手 | `server/discover` 自动处理 |
| `Mcp-Session-Id` | 不使用 |
| SSE transport | Streamable HTTP only |
| `uvicorn` 手动装配 | `mcp.streamable_http_app()` |

### 迁移步骤

1. 安装 `mcp==2.0.0`
2. 将 `FastMCP` 实例替换为 `MCPServer("name")`
3. 使用 `@mcp.tool()` 装饰工具函数
4. 使用 `mcp.run(transport="streamable-http", ...)` 启动服务
5. 或使用 `mcp.streamable_http_app()` 获取 ASGI 应用
6. 使用 `@mcp.custom_route()` 添加自定义 HTTP 端点
7. 删除所有 `initialize`、`Mcp-Session-Id` 相关代码
8. 删除所有会话管理和状态跟踪代码

### 添加新工具

只需在 `tools/` 目录新增模块，定义输入 Pydantic 模型，然后在 `server.py` 中：
1. 导入新函数
2. 使用 `@mcp.tool()` 装饰
3. 重启服务即可