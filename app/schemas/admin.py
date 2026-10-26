from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from datetime import datetime


class MerchantDeactivationResponse(BaseModel):
    id: UUID
    name: str
    email: str
    is_active: bool
    stores_suspended: int
    records_retained: bool


class MerchantRestorationResponse(BaseModel):
    id: UUID
    name: str
    email: str
    is_active: bool
    stores_restored: bool


class StoreRestorationResponse(BaseModel):
    id: UUID
    name: str
    owner_user_id: UUID
    verification_status: str
    records_retained: bool


class DeletedStoreResponse(BaseModel):
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
    deleted_at: datetime
    deleted_by: UUID | None
    deletion_reason: str | None
