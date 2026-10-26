from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import require_roles
from app.db.dependencies import get_db
from app.models.enums import (
    SalesDataSource,
    StoreVerificationStatus,
    UserRole,
    VoucherStatus,
)
from app.models.tables import (
    Invoice,
    InvoiceLineItem,
    SalesTransaction,
    Store,
    User,
    Voucher,
    VoucherRedemption,
)
from app.schemas.billing import (
    CreateInvoiceRequest,
    InvoiceLineItemResponse,
    InvoicePaymentStatusUpdate,
    InvoiceResponse,
    MerchantBillingDashboardResponse,
    RecordSaleRequest,
    SaleReceiptResponse,
)

router = APIRouter(prefix="/merchant/billing", tags=["Merchant Billing"])


def _invoice_response(invoice: Invoice, db: Session) -> InvoiceResponse:
    line_items = list(
        db.scalars(
            select(InvoiceLineItem)
            .where(InvoiceLineItem.invoice_id == invoice.id)
            .order_by(InvoiceLineItem.position.asc())
        ).all()
    )
    return InvoiceResponse(
        id=invoice.id,
        code=invoice.code,
        store_id=invoice.store_id,
        subtotal_paise=invoice.subtotal_paise,
        discount_paise=invoice.discount_paise,
        total_paise=invoice.total_paise,
        payment_status=invoice.payment_status,
        issued_at=invoice.issued_at,
        paid_at=invoice.paid_at,
        voucher_id=invoice.voucher_id,
        line_items=[
            InvoiceLineItemResponse(
                id=item.id,
                position=item.position,
                description=item.description,
                quantity=item.quantity,
                unit_price_paise=item.unit_price_paise,
                line_total_paise=item.line_total_paise,
            )
            for item in line_items
        ],
    )


@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a uniquely numbered invoice",
)
def create_invoice(
    invoice_data: CreateInvoiceRequest,
    current_merchant: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    store = db.scalar(
        select(Store)
        .where(
            Store.id == invoice_data.store_id,
            Store.owner_user_id == current_merchant.id,
        )
        .with_for_update()
    )
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    if store.verification_status not in {
        StoreVerificationStatus.pending.value,
        StoreVerificationStatus.verified.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Billing is unavailable for this store",
        )

    line_values = [
        {
            "position": position,
            "description": item.description,
            "quantity": item.quantity,
            "unit_price_paise": item.unit_price_paise,
            "line_total_paise": item.quantity * item.unit_price_paise,
        }
        for position, item in enumerate(invoice_data.items)
    ]
    subtotal_paise = sum(item["line_total_paise"] for item in line_values)

    voucher = None
    discount_paise = 0
    offer_id = None
    if invoice_data.voucher_code is not None:
        if store.verification_status != StoreVerificationStatus.verified.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Voucher discounts require a verified store",
            )
        voucher = db.scalar(
            select(Voucher)
            .where(Voucher.code == invoice_data.voucher_code)
            .with_for_update()
        )
        if voucher is None or voucher.store_id != store.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voucher not found for this store",
            )
        now = datetime.now(timezone.utc)
        if (
            voucher.status != VoucherStatus.claimed.value
            or voucher.expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Voucher is not available for redemption",
            )
        discount_paise = _voucher_discount(voucher, subtotal_paise)
        offer_id = voucher.offer_id

    now = datetime.now(timezone.utc)
    invoice = Invoice(
        code=f"INV-{uuid4().hex[:28].upper()}",
        merchant_id=current_merchant.id,
        store_id=store.id,
        voucher_id=voucher.id if voucher else None,
        subtotal_paise=subtotal_paise,
        discount_paise=discount_paise,
        total_paise=subtotal_paise - discount_paise,
        payment_status="unpaid",
    )
    try:
        db.add(invoice)
        db.flush()
        db.add_all(
            [
                InvoiceLineItem(invoice_id=invoice.id, **item)
                for item in line_values
            ]
        )
        db.add(
            SalesTransaction(
                store_id=store.id,
                offer_id=offer_id,
                voucher_id=voucher.id if voucher else None,
                gross_amount_paise=subtotal_paise,
                discount_paise=discount_paise,
                data_source=SalesDataSource.merchant_entered.value,
            )
        )
        if voucher is not None:
            voucher.status = VoucherStatus.redeemed.value
            voucher.redeemed_at = now
            db.add(
                VoucherRedemption(
                    voucher_id=voucher.id,
                    store_id=store.id,
                    redeemed_by=current_merchant.id,
                    bill_amount_paise=subtotal_paise,
                    discount_paise=discount_paise,
                    source="merchant_entered",
                )
            )
        db.commit()
        db.refresh(invoice)
    except Exception:
        db.rollback()
        raise

    return _invoice_response(invoice, db)


@router.get(
    "/invoices",
    response_model=list[InvoiceResponse],
    summary="List this merchant's invoices",
)
def list_merchant_invoices(
    current_merchant: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
    payment_status: str | None = Query(default=None, pattern="^(paid|unpaid)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[InvoiceResponse]:
    statement = select(Invoice).where(
        Invoice.merchant_id == current_merchant.id
    )
    if payment_status is not None:
        statement = statement.where(Invoice.payment_status == payment_status)
    invoices = list(
        db.scalars(
            statement.order_by(Invoice.issued_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return [_invoice_response(invoice, db) for invoice in invoices]


@router.get(
    "/invoices/{invoice_code}",
    response_model=InvoiceResponse,
    summary="Get one of this merchant's invoices",
)
def get_merchant_invoice(
    invoice_code: str,
    current_merchant: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.code == invoice_code,
            Invoice.merchant_id == current_merchant.id,
        )
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return _invoice_response(invoice, db)


@router.patch(
    "/invoices/{invoice_code}/payment-status",
    response_model=InvoiceResponse,
    summary="Mark an invoice paid or unpaid",
)
def update_invoice_payment_status(
    invoice_code: str,
    payment_update: InvoicePaymentStatusUpdate,
    current_merchant: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    invoice = db.scalar(
        select(Invoice)
        .where(
            Invoice.code == invoice_code,
            Invoice.merchant_id == current_merchant.id,
        )
        .with_for_update()
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    invoice.payment_status = payment_update.payment_status
    invoice.paid_at = (
        datetime.now(timezone.utc)
        if payment_update.payment_status == "paid"
        else None
    )
    try:
        db.commit()
        db.refresh(invoice)
    except Exception:
        db.rollback()
        raise
    return _invoice_response(invoice, db)


@router.get(
    "/dashboard",
    response_model=MerchantBillingDashboardResponse,
    summary="Get this merchant's invoice totals",
)
def get_merchant_billing_dashboard(
    current_merchant: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> MerchantBillingDashboardResponse:
    rows = db.execute(
        select(
            Invoice.payment_status,
            Invoice.total_paise,
        ).where(Invoice.merchant_id == current_merchant.id)
    ).all()
    paid = [int(total) for payment_status, total in rows if payment_status == "paid"]
    unpaid = [
        int(total) for payment_status, total in rows if payment_status == "unpaid"
    ]
    return MerchantBillingDashboardResponse(
        invoices_count=len(rows),
        paid_invoices_count=len(paid),
        unpaid_invoices_count=len(unpaid),
        invoiced_total_paise=sum(paid) + sum(unpaid),
        paid_total_paise=sum(paid),
        unpaid_total_paise=sum(unpaid),
    )


def _voucher_discount(voucher: Voucher, bill_amount_paise: int) -> int:
    terms = voucher.terms_snapshot
    minimum = terms.get("min_order_paise", 0)
    discount_type = terms.get("type")
    value = terms.get("value")
    maximum = terms.get("max_discount_paise")

    if not isinstance(minimum, int) or not isinstance(value, int):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Voucher terms are incomplete; contact support",
        )
    if bill_amount_paise < minimum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bill amount does not meet the voucher minimum order",
        )

    if discount_type == "percent" and 1 <= value <= 100:
        discount = bill_amount_paise * value // 100
    elif discount_type == "fixed" and value > 0:
        discount = value * 100
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Voucher discount terms are invalid; contact support",
        )
    if maximum is not None:
        if not isinstance(maximum, int) or maximum < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Voucher discount cap is invalid; contact support",
            )
        discount = min(discount, maximum)
    return min(discount, bill_amount_paise)


@router.post(
    "/sales",
    response_model=SaleReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a completed sale and optionally redeem a voucher",
)
def record_sale(
    sale_data: RecordSaleRequest,
    current_merchant: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> SaleReceiptResponse:
    store = db.scalar(
        select(Store)
        .where(
            Store.id == sale_data.store_id,
            Store.owner_user_id == current_merchant.id,
        )
        .with_for_update()
    )
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    if store.verification_status not in {
        StoreVerificationStatus.pending.value,
        StoreVerificationStatus.verified.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Billing is unavailable for this store",
        )

    voucher = None
    discount_paise = 0
    offer_id = None
    if sale_data.voucher_code is not None:
        if store.verification_status != StoreVerificationStatus.verified.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Voucher discounts require a verified store",
            )
        voucher = db.scalar(
            select(Voucher)
            .where(Voucher.code == sale_data.voucher_code)
            .with_for_update()
        )
        if voucher is None or voucher.store_id != store.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voucher not found for this store",
            )
        now = datetime.now(timezone.utc)
        if (
            voucher.status != VoucherStatus.claimed.value
            or voucher.expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Voucher is not available for redemption",
            )

        discount_paise = _voucher_discount(
            voucher, sale_data.gross_amount_paise
        )
        offer_id = voucher.offer_id

    transaction = SalesTransaction(
        store_id=store.id,
        offer_id=offer_id,
        voucher_id=voucher.id if voucher else None,
        gross_amount_paise=sale_data.gross_amount_paise,
        discount_paise=discount_paise,
        data_source=SalesDataSource.merchant_entered.value,
    )
    db.add(transaction)

    if voucher is not None:
        now = datetime.now(timezone.utc)
        voucher.status = VoucherStatus.redeemed.value
        voucher.redeemed_at = now
        db.add(
            VoucherRedemption(
                voucher_id=voucher.id,
                store_id=store.id,
                redeemed_by=current_merchant.id,
                bill_amount_paise=sale_data.gross_amount_paise,
                discount_paise=discount_paise,
                source="merchant_entered",
            )
        )

    try:
        db.commit()
        db.refresh(transaction)
    except Exception:
        db.rollback()
        raise

    return SaleReceiptResponse(
        id=transaction.id,
        store_id=transaction.store_id,
        offer_id=transaction.offer_id,
        voucher_id=transaction.voucher_id,
        gross_amount_paise=transaction.gross_amount_paise,
        discount_paise=transaction.discount_paise,
        net_amount_paise=(
            transaction.gross_amount_paise - transaction.discount_paise
        ),
        occurred_at=transaction.occurred_at,
        data_source=transaction.data_source,
    )
