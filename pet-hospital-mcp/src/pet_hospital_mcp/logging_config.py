from __future__ import annotations

import time
from typing import Any

import structlog

logger = structlog.get_logger()

SENSITIVE_FIELDS = {"ownerPhone", "ownerAddr", "chipNo", "ownerphone", "owneraddr", "chipno"}


def _mask_sensitive(data: Any) -> Any:
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k in SENSITIVE_FIELDS or k.lower() in SENSITIVE_FIELDS:
                result[k] = "***"
            elif isinstance(v, (dict, list)):
                result[k] = _mask_sensitive(v)
            else:
                result[k] = v
        return result
    if isinstance(data, list):
        return [_mask_sensitive(item) for item in data]
    return data


def log_tool_call(
    tool_name: str,
    params: dict[str, Any],
    status: str,
    duration_ms: float,
    error: str | None = None,
) -> None:
    masked_params = _mask_sensitive(params)
    logger.info(
        "tool_call",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        tool_name=tool_name,
        params=masked_params,
        status=status,
        duration_ms=round(duration_ms, 2),
        error=error,
    )