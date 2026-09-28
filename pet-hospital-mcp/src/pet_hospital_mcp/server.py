from __future__ import annotations

import asyncio
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import MCPError

from pet_hospital_mcp.config import settings
from pet_hospital_mcp.rest_client import PetHospitalClient, BackendError
from pet_hospital_mcp.logging_config import log_tool_call
from pet_hospital_mcp.tools.list_pets import ListPetsInput

mcp = MCPServer("Pet Hospital", log_level="INFO")

_ERROR_CODE_MAP: dict[str, int] = {
    "VALIDATION_ERROR": -32001,
    "BACKEND_TIMEOUT": -32002,
    "BACKEND_UNAVAILABLE": -32003,
    "BACKEND_API_ERROR": -32004,
    "BACKEND_INVALID_RESPONSE": -32005,
    "INTERNAL_ERROR": -32006,
}


def _as_mcp_error(error: BackendError) -> MCPError:
    code = _ERROR_CODE_MAP.get(error.code, -32006)
    return MCPError(code=code, message=f"{error.code}: {error.message}", data=error.to_response())


def _register(server: MCPServer) -> None:
    @server.tool()
    async def list_pets(
        q: str | None = None,
        name: str | None = None,
        ownerName: str | None = None,
        ownerPhone: str | None = None,
        species: str | None = None,
        doctor: str | None = None,
        disease: str | None = None,
        status: str | None = None,
        min: float | None = None,
        max: float | None = None,
        sortBy: str | None = None,
        order: str | None = None,
        page: int = 1,
        pageSize: int = 10,
    ) -> dict[str, object]:
        """查询宠物医院档案列表。

        通过 GET /api/v1/pets 调用后端 Go REST API，支持多维度过滤、排序和分页。

        适用场景：
        - 按种类、医生、状态等筛选宠物档案
        - 按总花费范围查询
        - 按指定字段排序和分页浏览

        返回值：包含 items(档案列表)、total(总数)、page(当前页)、pageSize(每页大小)、
        totalPages(总页数)、totalCost(总花费) 的对象。

        参数说明：
        - q: 全文检索关键词
        - name: 宠物名称
        - ownerName: 主人姓名
        - ownerPhone: 主人电话
        - species: 种类（犬/猫/兔/鸟/鱼/龟/鼠）
        - doctor: 医生
        - disease: 疾病
        - status: 就诊状态（待就诊/就诊中/住院中/已康复/慢性病随访）
        - min/max: 总花费区间
        - sortBy: 排序字段（name/totalCost/createdAt）
        - order: 排序方向（asc/desc）
        - page: 页码（>=1）
        - pageSize: 每页大小（1-500）
        """
        try:
            input_data = ListPetsInput(
                q=q, name=name, ownerName=ownerName, ownerPhone=ownerPhone,
                species=species, doctor=doctor, disease=disease, status=status,
                min=min, max=max, sortBy=sortBy, order=order, page=page, pageSize=pageSize,
            )
        except Exception as e:
            log_tool_call("list_pets", {"error": str(e)}, "VALIDATION_ERROR", 0, str(e))
            raise _as_mcp_error(
                BackendError(
                    "VALIDATION_ERROR",
                    f"Invalid input: {e}",
                    {"error": str(e)},
                )
            ) from e

        params = input_data.model_dump(exclude_none=True)
        log_tool_call("list_pets", params, "START", 0)

        async with PetHospitalClient(base_url=settings.PET_HOSPITAL_BASE_URL) as client:
            try:
                result = await client.list_pets(**params)
                return {
                    "items": [item.model_dump(mode="json", exclude_none=True) for item in result.items],
                    "total": result.total,
                    "page": result.page,
                    "pageSize": result.pageSize,
                    "totalPages": result.totalPages,
                    "totalCost": result.totalCost,
                }
            except BackendError as e:
                log_tool_call("list_pets", params, "FAILURE", 0, e.message)
                raise _as_mcp_error(e) from e

    @server.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})


_register(mcp)


def create_app() -> Any:
    server = MCPServer("Pet Hospital", log_level="INFO")
    _register(server)
    return server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        host=settings.MCP_HOST,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"],
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"],
        ),
    )


app = create_app()