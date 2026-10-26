from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

BIGINT_MAX = 9_223_372_036_854_775_807


class RecordSaleRequest(BaseModel):
    store_id: UUID
    gross_amount_paise: int = Field(
        ge=0,
        le=BIGINT_MAX,
        description="Total bill before voucher discount, in paise.",
    )
    voucher_code: str | None = Field(default=None, min_length=1, max_length=128)


class SaleReceiptResponse(BaseModel):
    id: UUID
    store_id: UUID
    offer_id: UUID | None
    voucher_id: UUID | None
    gross_amount_paise: int = Field(description="Total bill before discount, in paise.")
    discount_paise: int = Field(description="Voucher discount, in paise.")
    net_amount_paise: int = Field(description="Bill after discount, before tax, in paise.")
    occurred_at: datetime
    data_source: str


class InvoiceLineItemCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    quantity: int = Field(gt=0, le=1_000_000)
    unit_price_paise: int = Field(ge=0, le=BIGINT_MAX)

    @model_validator(mode="after")
    def validate_line_total(self) -> "InvoiceLineItemCreate":
        if self.quantity * self.unit_price_paise > BIGINT_MAX:
            raise ValueError("line total exceeds the supported maximum")
        return self


class CreateInvoiceRequest(BaseModel):
    store_id: UUID
    items: list[InvoiceLineItemCreate] = Field(min_length=1, max_length=100)
    voucher_code: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_subtotal(self) -> "CreateInvoiceRequest":
        subtotal = sum(
            item.quantity * item.unit_price_paise for item in self.items
        )
        if subtotal > BIGINT_MAX:
            raise ValueError("invoice subtotal exceeds the supported maximum")
        return self


class InvoiceLineItemResponse(InvoiceLineItemCreate):
    id: UUID
    position: int
    line_total_paise: int


class InvoiceResponse(BaseModel):
    id: UUID
    code: str
    store_id: UUID
    subtotal_paise: int
    discount_paise: int
    total_paise: int
    payment_status: Literal["paid", "unpaid"]
    issued_at: datetime
    paid_at: datetime | None
    voucher_id: UUID | None
    line_items: list[InvoiceLineItemResponse]


class InvoicePaymentStatusUpdate(BaseModel):
    payment_status: Literal["paid", "unpaid"]


class MerchantBillingDashboardResponse(BaseModel):
    invoices_count: int
    paid_invoices_count: int
    unpaid_invoices_count: int
    invoiced_total_paise: int
    paid_total_paise: int
    unpaid_total_paise: int
