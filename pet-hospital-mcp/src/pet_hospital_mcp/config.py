from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    MCP_HOST: str = "127.0.0.1"
    MCP_PORT: int = 8000
    PET_HOSPITAL_BASE_URL: str = "http://127.0.0.1:8080"

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            MCP_HOST=os.environ.get("MCP_HOST", "127.0.0.1"),
            MCP_PORT=int(os.environ.get("MCP_PORT", "8000")),
            PET_HOSPITAL_BASE_URL=os.environ.get("PET_HOSPITAL_BASE_URL", "http://127.0.0.1:8080"),
        )


settings = Settings.load()