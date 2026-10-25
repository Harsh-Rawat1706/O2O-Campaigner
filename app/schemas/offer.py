from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OfferCreate(BaseModel):
    store_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    type: Literal["percent", "fixed"]
    value: int = Field(gt=0)
    min_order_paise: int = Field(default=0, ge=0)
    max_discount_paise: int | None = Field(default=None, gt=0)
    starts_at: datetime
    ends_at: datetime
    max_claims: int | None = Field(default=None, gt=0)
    per_customer_limit: int = Field(default=1, gt=0)
    terms: str | None = None

    @model_validator(mode="after")
    def validate_offer_terms(self) -> "OfferCreate":
        if self.starts_at.utcoffset() is None or self.ends_at.utcoffset() is None:
            raise ValueError("starts_at and ends_at must include a timezone")

        duration = self.ends_at - self.starts_at
        if duration <= timedelta(0):
            raise ValueError("ends_at must be later than starts_at")
        if duration > timedelta(days=90):
            raise ValueError("Offer duration cannot exceed 90 days")

        if self.type == "percent":
            if self.value > 70:
                raise ValueError("Percentage discount cannot exceed 70")
            if self.value > 20 and self.max_discount_paise is None:
                raise ValueError(
                    "A max_discount_paise cap is required for discounts above 20%"
                )
        elif self.min_order_paise > 0 and self.value * 100 >= self.min_order_paise:
            raise ValueError(
                "Fixed discount in rupees must be less than the minimum order in paise"
            )

        return self


class OfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    store_id: UUID
    title: str
    description: str | None
    type: str
    value: int
    min_order_paise: int
    max_discount_paise: int | None
    starts_at: datetime
    ends_at: datetime
    status: str
    max_claims: int | None
    per_customer_limit: int
    terms: str | None
    version: int
    created_at: datetime
