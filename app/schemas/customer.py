from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CustomerStoreSummary(BaseModel):
    id: UUID
    name: str
    address: str
    lat: Decimal
    lng: Decimal
    google_maps_link: str | None
    distance_km: float


class CustomerOfferResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    type: str
    value: int
    min_order_paise: int
    max_discount_paise: int | None
    starts_at: datetime
    ends_at: datetime
    store: CustomerStoreSummary


class CustomerVoucherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    offer_id: UUID
    store_id: UUID
    status: str
    claimed_at: datetime
    expires_at: datetime


class CustomerVoucherDetailResponse(CustomerVoucherResponse):
    offer_title: str
    store_name: str
