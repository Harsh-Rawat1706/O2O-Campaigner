from uuid import UUID

from pydantic import BaseModel


class AdminOfferPerformance(BaseModel):
    offer_id: UUID
    title: str
    status: str
    published: bool
    merchant_id: UUID
    merchant_name: str
    store_id: UUID
    store_name: str
    vouchers_claimed: int
    vouchers_used: int


class AdminMerchantPerformance(BaseModel):
    merchant_id: UUID
    merchant_name: str
    is_active: bool
    offers_created: int
    offers_published: int
    vouchers_claimed: int
    vouchers_used: int


class AdminDashboardResponse(BaseModel):
    merchants_total: int
    merchants_active: int
    offers_total: int
    offers_published: int
    offers_by_status: dict[str, int]
    vouchers_claimed: int
    vouchers_used: int
    top_offers: list[AdminOfferPerformance]
    offers: list[AdminOfferPerformance]
    merchants_by_performance: list[AdminMerchantPerformance]
    offers_offset: int
    offers_limit: int
