from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from pydantic import ValidationError

from pet_hospital_mcp.errors import GoAPIResponse, PetListResponse
from pet_hospital_mcp.logging_config import log_tool_call


class BackendError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_response(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class PetHospitalClient:
    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def __aenter__(self) -> PetHospitalClient:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def list_pets(
        self,
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
    ) -> PetListResponse:
        params: dict[str, Any] = {}
        if q is not None:
            params["q"] = q
        if name is not None:
            params["name"] = name
        if ownerName is not None:
            params["ownerName"] = ownerName
        if ownerPhone is not None:
            params["ownerPhone"] = ownerPhone
        if species is not None:
            params["species"] = species
        if doctor is not None:
            params["doctor"] = doctor
        if disease is not None:
            params["disease"] = disease
        if status is not None:
            params["status"] = status
        if min is not None:
            params["min"] = min
        if max is not None:
            params["max"] = max
        if sortBy is not None:
            params["sortBy"] = sortBy
        if order is not None:
            params["order"] = order
        params["page"] = page
        params["pageSize"] = pageSize

        start = time.monotonic()
        attempt = 0
        last_error: BackendError | None = None

        while attempt < self.max_retries:
            attempt += 1
            try:
                client = await self._get_client()
                response = await client.get("/api/v1/pets", params=params)
                elapsed = (time.monotonic() - start) * 1000

                if response.status_code >= 500:
                    last_error = BackendError(
                        "BACKEND_API_ERROR",
                        f"Backend returned HTTP {response.status_code}",
                        {"status_code": response.status_code, "attempt": attempt},
                    )
                    continue

                if response.status_code >= 400:
                    log_tool_call("list_pets", params, "FAILURE", elapsed, f"Backend HTTP {response.status_code}")
                    raise BackendError(
                        "BACKEND_API_ERROR",
                        f"Backend returned HTTP {response.status_code}",
                        {"status_code": response.status_code},
                    )

                try:
                    go_response = GoAPIResponse.model_validate_json(response.text)
                except ValidationError:
                    log_tool_call("list_pets", params, "FAILURE", elapsed, "Invalid JSON from backend")
                    raise BackendError(
                        "BACKEND_INVALID_RESPONSE",
                        "Backend returned an invalid response envelope",
                        {"content_type": "invalid_json"},
                    )
                except ValueError:
                    log_tool_call("list_pets", params, "FAILURE", elapsed, "Invalid JSON from backend")
                    raise BackendError(
                        "BACKEND_INVALID_RESPONSE",
                        "Backend returned invalid JSON",
                        {"content_type": "invalid_json"},
                    )

                if go_response.code != 200:
                    log_tool_call("list_pets", params, "FAILURE", elapsed, f"Backend code {go_response.code}")
                    raise BackendError(
                        "BACKEND_API_ERROR",
                        go_response.message,
                        {"backend_code": go_response.code},
                    )

                data = go_response.data
                try:
                    pet_list = PetListResponse(
                        items=data.get("items", []),
                        total=data.get("total", 0),
                        page=data.get("page", 1),
                        pageSize=data.get("pageSize", 10),
                        totalPages=data.get("totalPages", 0),
                        totalCost=data.get("totalCost", 0.0),
                    )
                except ValidationError:
                    log_tool_call("list_pets", params, "FAILURE", elapsed, "Backend data model mismatch")
                    raise BackendError(
                        "BACKEND_INVALID_RESPONSE",
                        "Backend response does not match the expected data model",
                        {"error": "schema_mismatch"},
                    )

                log_tool_call("list_pets", params, "SUCCESS", elapsed)
                return pet_list

            except BackendError:
                raise

            except (httpx.TimeoutException, asyncio.TimeoutError) as e:
                last_error = BackendError(
                    "BACKEND_TIMEOUT",
                    f"Backend request timed out",
                    {"attempt": attempt},
                )
                if attempt >= self.max_retries:
                    elapsed = (time.monotonic() - start) * 1000
                    log_tool_call("list_pets", params, "FAILURE", elapsed, f"Timeout after {attempt} attempts")
                    raise last_error from e
                await asyncio.sleep(0.5 * attempt)

            except httpx.ConnectError as e:
                last_error = BackendError(
                    "BACKEND_UNAVAILABLE",
                    "Backend is unavailable",
                    {"attempt": attempt},
                )
                if attempt >= self.max_retries:
                    elapsed = (time.monotonic() - start) * 1000
                    log_tool_call("list_pets", params, "FAILURE", elapsed, "Backend unreachable")
                    raise last_error from e
                await asyncio.sleep(0.5 * attempt)

            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                log_tool_call("list_pets", params, "FAILURE", elapsed, f"Unexpected error: {e}")
                raise BackendError(
                    "INTERNAL_ERROR",
                    f"Unexpected error: {e}",
                    {"error_type": type(e).__name__},
                ) from e

        elapsed = (time.monotonic() - start) * 1000
        raise last_error or BackendError("INTERNAL_ERROR", "Unexpected error", {})