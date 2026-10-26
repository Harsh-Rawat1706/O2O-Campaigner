from datetime import datetime
from decimal import Decimal
from urllib.parse import urlsplit
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1)
    lat: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"))
    lng: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"))
    category_id: UUID | None = None
    category_name: str | None = Field(default=None, min_length=1, max_length=100)
    google_maps_link: str = Field(min_length=1, max_length=2048)
    hours: dict[str, object] = Field(default_factory=dict)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("category_name")
    @classmethod
    def normalize_category_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("category_name cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_category_selection(self) -> "StoreCreate":
        if self.category_id is not None and self.category_name is not None:
            raise ValueError("Provide category_id or category_name, not both")
        return self

    @field_validator("google_maps_link")
    @classmethod
    def validate_google_maps_link(cls, value: str) -> str:
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").lower()
        valid_google_maps_url = parsed.scheme == "https" and (
            (
                hostname in {"google.com", "www.google.com"}
                and parsed.path.startswith("/maps")
            )
            or hostname == "maps.google.com"
            or (
                hostname == "maps.app.goo.gl"
                and bool(parsed.path.strip("/"))
            )
            or (
                hostname == "goo.gl"
                and parsed.path.startswith("/maps/")
            )
        )
        if not valid_google_maps_url:
            raise ValueError(
                "Provide a valid HTTPS Google Maps sharing link"
            )
        return value


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    category_id: UUID | None
    name: str
    address: str
    lat: Decimal
    lng: Decimal
    google_maps_link: str | None
    hours: dict[str, object]
    phone: str | None
    verification_status: str
    created_at: datetime


class StoreVerificationRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=1000)


class StoreCategoryResponse(BaseModel):
    id: UUID
    name: str
