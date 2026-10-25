from datetime import datetime
from decimal import Decimal
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1)
    lat: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"))
    lng: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"))
    category_id: UUID | None = None
    hours: dict[str, object] = Field(default_factory=dict)
    phone: str | None = Field(default=None, max_length=20)


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    category_id: UUID | None
    name: str
    address: str
    lat: Decimal
    lng: Decimal
    hours: dict[str, object]
    phone: str | None
    verification_status: str
    created_at: datetime


class StoreVerificationRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=1000)
