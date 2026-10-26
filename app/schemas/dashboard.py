from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.billing import MerchantBillingDashboardResponse

class MerchantOfferPerformance(BaseModel):
    offer_id: UUID
    title: str
    status: str
    starts_at: datetime
    ends_at: datetime
    sales_count: int
    gross_sales_paise: int
    discounts_paise: int
    net_sales_paise: int
    vouchers_claimed: int
    vouchers_used: int


class MerchantOfferDashboard(BaseModel):
    gross_sales_paise: int
    discounts_paise: int
    net_sales_paise: int
    sales_count: int
    offers: list[MerchantOfferPerformance]


class MerchantDashboardResponse(BaseModel):
    billing: MerchantBillingDashboardResponse
    offer_analytics: MerchantOfferDashboard | None
