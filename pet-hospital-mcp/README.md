# Pet Hospital MCP Server

MCP 服务器，将 Go 宠物医院 REST API 的能力暴露给 AI Agent。

## 技术栈

- **Python 3.11+**
- **MCP SDK 2.0.0** (`mcp==2.0.0`)
- **MCP 协议版本**: `2026-07-28`
- **MCPServer** + **Streamable HTTP** 无状态模型
- **httpx** - 后端 HTTP 客户端
- **Pydantic** - 输入校验与数据模型
- **structlog** - JSON 日志

## 依赖安装

```bash
cd pet-hospital-mcp
pip install -e .
pip install pytest pytest-asyncio httpx respx
```

## 前置条件

Go 宠物医院服务必须先启动：

```bash
cd windows
./pethospital.exe
# 或
pethospital.exe
```

默认地址：`http://127.0.0.1:8080`

## 启动 MCP 服务

```bash
cd pet-hospital-mcp
python -m pet_hospital_mcp
```

或指定端口和地址：

```bash
MCP_HOST=0.0.0.0 MCP_PORT=8000 PET_HOSPITAL_BASE_URL=http://127.0.0.1:8080 python -m pet_hospital_mcp
```

### 可配置环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MCP_HOST` | `127.0.0.1` | MCP 服务监听地址 |
| `MCP_PORT` | `8000` | MCP 服务监听端口 |
| `PET_HOSPITAL_BASE_URL` | `http://127.0.0.1:8080` | Go 后端地址 |

## MCP 端点

- **Streamable HTTP**: `http://127.0.0.1:8000/mcp`
- **健康检查**: `http://127.0.0.1:8000/health`

## 验证

### 使用 MCP Inspector

```bash
uv run mcp dev src/pet_hospital_mcp/server.py
```

### 使用 SDK 2.x 客户端验证无状态连接

```python
import asyncio
from mcp import Client

async def main():
    async with Client("http://127.0.0.1:8000/mcp") as client:
        # 发现工具
        tools = await client.list_tools()
        print(f"发现 {len(tools)} 个工具")

        # 调用 list_pets
        result = await client.call_tool("list_pets", {
            "species": "犬",
            "page": 1,
            "pageSize": 10,
        })
        print(result.structured_content)

asyncio.run(main())
```

**无状态连接特性**：
- 不发送旧 `initialize` 请求
- 不要求或返回 `Mcp-Session-Id`
- 每次请求独立，使用 `server/discover` 发现端点

### 调用 list_pets 示例

```bash
# 查询所有犬类
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method":"tools/call","params":{"name":"list_pets","arguments":{"species":"犬","page":1,"pageSize":10}}}'
```

### 健康检查

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

## 单元测试

```bash
cd pet-hospital-mcp
pytest -q
```

预期结果：全部测试通过（27 个），覆盖以下场景：
- 正常调用及全部过滤/排序/分页参数转发
- 输入参数校验失败
- Go REST API 返回 4xx/5xx（含重试）
- 超时和连接异常
- 后端返回非法 JSON 或数据模型不符
- MCP 工具注册和 JSON Schema
- HTTP 端点上的无状态发现/调用（`server/discover`、`tools/list`、`tools/call`）
- 无 `initialize`、无 `Mcp-Session-Id`（协议 2026-07-28）
- 结构化错误码经 MCP 传输
- /health 端点

## 工具说明

### list_pets

**唯一工具**。查询宠物医院档案列表。

参数：
- `q`: 全文检索关键词
- `name`: 宠物名称
- `ownerName`: 主人姓名
- `ownerPhone`: 主人电话（日志脱敏）
- `species`: 种类（犬/猫/兔/鸟/鱼/龟/鼠）
- `doctor`: 医生
- `disease`: 疾病
- `status`: 就诊状态（待就诊/就诊中/住院中/已康复/慢性病随访）
- `min`: 最小总花费（>=0）
- `max`: 最大总花费（>=0）
- `sortBy`: 排序字段（name/totalCost/createdAt）
- `order`: 排序方向（asc/desc）
- `page`: 页码（>=1）
- `pageSize`: 每页大小（1-500）

返回：`{items, total, page, pageSize, totalPages, totalCost}`

## 错误处理

统一结构化错误格式。工具执行失败时抛出 `MCPError`，客户端收到的 JSON-RPC error 携带完整结构：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "可读错误信息",
    "details": {}
  }
}
```

错误码：`VALIDATION_ERROR`, `BACKEND_TIMEOUT`, `BACKEND_UNAVAILABLE`, `BACKEND_API_ERROR`, `BACKEND_INVALID_RESPONSE`, `INTERNAL_ERROR`

各错误码对应的 JSON-RPC 数字 code：`-32001` ~ `-32006`，`data` 字段即上述结构化错误对象。

## 日志

日志包含 `timestamp`, `tool_name`, `params`, `status`, `duration_ms`。
`ownerPhone`, `ownerAddr`, `chipNo` 及其 snake_case 写法在日志中递归脱敏。

## 项目结构

```
pet-hospital-mcp/
├── pyproject.toml
├── README.md
├── UPGRADE_PROMPT.md
├── src/
│   └── pet_hospital_mcp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       ├── server.py
│       ├── rest_client.py
│       ├── errors.py
│       ├── logging_config.py
│       └── tools/
│           ├── __init__.py
│           └── list_pets.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_list_pets.py
    ├── test_server.py
    └── test_http_endpoint.py
```

## 未实现阶段二工具

本次仅实现 `list_pets` 工具。后续阶段新增工具时，只需在 `tools/` 目录增加模块并复用 REST 客户端、日志和错误约定。