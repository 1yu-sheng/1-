from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SuccessResponse(BaseModel):
    code: int = 200
    message: str = "ok"
    data: dict[str, Any] = Field(default_factory=dict)
    time: str = Field(default="")


class PetItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    species: str
    breed: str = ""
    gender: str = ""
    ageMonths: int = 0
    ownerName: str = ""
    ownerPhone: str = ""
    ownerAddr: str = ""
    chipNo: str = ""
    disease: str = ""
    doctor: str = ""
    status: str = ""
    totalCost: float = 0.0
    records: list[dict[str, Any]] | None = None
    charges: list[dict[str, Any]] | None = None


class PetListResponse(BaseModel):
    items: list[PetItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    pageSize: int = 10
    totalPages: int = 0
    totalCost: float = 0.0


class GoAPIResponse(BaseModel):
    code: int
    message: str
    data: dict[str, Any]
    time: str


VALID_SPECIES: list[str] = ["犬", "猫", "兔", "鸟", "鱼", "龟", "鼠"]
VALID_STATUSES: list[str] = ["待就诊", "就诊中", "住院中", "已康复", "慢性病随访"]
VALID_SORT_BY: list[str] = ["name", "totalCost", "createdAt"]
VALID_ORDERS: list[str] = ["asc", "desc"]