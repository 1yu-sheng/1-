from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class ListPetsInput(BaseModel):
    q: str | None = None
    name: str | None = None
    ownerName: str | None = None
    ownerPhone: str | None = None
    species: str | None = Field(default=None)
    doctor: str | None = None
    disease: str | None = None
    status: str | None = Field(default=None)
    min: float | None = Field(default=None, ge=0)
    max: float | None = Field(default=None, ge=0)
    sortBy: str | None = None
    order: str | None = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=500)

    @field_validator("species")
    @classmethod
    def validate_species(cls, v: str | None) -> str | None:
        if v is not None and v not in ("犬", "猫", "兔", "鸟", "鱼", "龟", "鼠"):
            raise ValueError(f"species must be one of 犬, 猫, 兔, 鸟, 鱼, 龟, 鼠, got {v!r}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        valid = {"待就诊", "就诊中", "住院中", "已康复", "慢性病随访"}
        if v is not None and v not in valid:
            raise ValueError(f"status must be one of {valid}, got {v!r}")
        return v

    @field_validator("sortBy")
    @classmethod
    def validate_sort_by(cls, v: str | None) -> str | None:
        valid = {"name", "totalCost", "createdAt"}
        if v is not None and v not in valid:
            raise ValueError(f"sortBy must be one of {valid}, got {v!r}")
        return v

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: str | None) -> str | None:
        valid = {"asc", "desc"}
        if v is not None and v not in valid:
            raise ValueError(f"order must be one of {valid}, got {v!r}")
        return v

    @model_validator(mode="after")
    def validate_min_max(self) -> ListPetsInput:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must be less than or equal to max")
        return self

    model_config = {"extra": "forbid"}


def validate_list_pets_input(**kwargs) -> ListPetsInput:
    return ListPetsInput(**kwargs)