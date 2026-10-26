from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import require_roles
from app.db.dependencies import get_db
from app.models.enums import (
    OfferStatus,
    StoreVerificationStatus,
    UserRole,
    VoucherStatus,
)
from app.models.tables import Invoice, Offer, SalesTransaction, Store, User, Voucher
from app.schemas.admin_dashboard import (
    AdminDashboardResponse,
    AdminMerchantPerformance,
    AdminOfferPerformance,
)
from app.schemas.dashboard import (
    MerchantOfferDashboard,
    MerchantDashboardResponse,
    MerchantOfferPerformance,
)
from app.schemas.billing import MerchantBillingDashboardResponse

router = APIRouter(tags=["Dashboards"])
admin_dashboard_router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


@router.get(
    "/merchant/dashboard",
    response_model=MerchantDashboardResponse,
    summary="Get merchant sales and offer performance",
)
def get_merchant_dashboard(
    current_merchant: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> MerchantDashboardResponse:
    invoice_rows = db.execute(
        select(Invoice.payment_status, Invoice.total_paise).where(
            Invoice.merchant_id == current_merchant.id
        )
    ).all()
    paid_invoices = [
        int(total) for payment_status, total in invoice_rows
        if payment_status == "paid"
    ]
    unpaid_invoices = [
        int(total) for payment_status, total in invoice_rows
        if payment_status == "unpaid"
    ]
    billing_dashboard = MerchantBillingDashboardResponse(
        invoices_count=len(invoice_rows),
        paid_invoices_count=len(paid_invoices),
        unpaid_invoices_count=len(unpaid_invoices),
        invoiced_total_paise=sum(paid_invoices) + sum(unpaid_invoices),
        paid_total_paise=sum(paid_invoices),
        unpaid_total_paise=sum(unpaid_invoices),
    )

    has_verified_store = db.scalar(
        select(
            func.count(Store.id)
        ).where(
            Store.owner_user_id == current_merchant.id,
            Store.verification_status
            == StoreVerificationStatus.verified.value,
        )
    )
    if not has_verified_store:
        return MerchantDashboardResponse(
            billing=billing_dashboard,
            offer_analytics=None,
        )

    totals = db.execute(
        select(
            func.coalesce(func.sum(SalesTransaction.gross_amount_paise), 0),
            func.coalesce(func.sum(SalesTransaction.discount_paise), 0),
            func.count(SalesTransaction.id),
        )
        .join(Store, SalesTransaction.store_id == Store.id)
        .where(
            Store.owner_user_id == current_merchant.id,
            Store.verification_status
            == StoreVerificationStatus.verified.value,
        )
    ).one()

    sales_by_offer = (
        select(
            SalesTransaction.offer_id.label("offer_id"),
            func.sum(SalesTransaction.gross_amount_paise).label(
                "gross_sales_paise"
            ),
            func.sum(SalesTransaction.discount_paise).label(
                "discounts_paise"
            ),
            func.count(SalesTransaction.id).label("sales_count"),
        )
        .join(Store, SalesTransaction.store_id == Store.id)
        .where(
            Store.owner_user_id == current_merchant.id,
            Store.verification_status
            == StoreVerificationStatus.verified.value,
        )
        .group_by(SalesTransaction.offer_id)
        .subquery()
    )
    vouchers_by_offer = (
        select(
            Voucher.offer_id.label("offer_id"),
            func.count(Voucher.id).label("vouchers_claimed"),
            func.sum(
                case(
                    (Voucher.status == VoucherStatus.redeemed.value, 1),
                    else_=0,
                )
            ).label("vouchers_used"),
        )
        .join(Store, Voucher.store_id == Store.id)
        .where(
            Store.owner_user_id == current_merchant.id,
            Store.verification_status
            == StoreVerificationStatus.verified.value,
        )
        .group_by(Voucher.offer_id)
        .subquery()
    )

    gross_sales = func.coalesce(sales_by_offer.c.gross_sales_paise, 0)
    discounts = func.coalesce(sales_by_offer.c.discounts_paise, 0)
    offer_rows = db.execute(
        select(
            Offer,
            gross_sales,
            discounts,
            func.coalesce(sales_by_offer.c.sales_count, 0),
            func.coalesce(vouchers_by_offer.c.vouchers_claimed, 0),
            func.coalesce(vouchers_by_offer.c.vouchers_used, 0),
        )
        .join(Store, Offer.store_id == Store.id)
        .outerjoin(
            sales_by_offer,
            sales_by_offer.c.offer_id == Offer.id,
        )
        .outerjoin(
            vouchers_by_offer,
            vouchers_by_offer.c.offer_id == Offer.id,
        )
        .where(
            Store.owner_user_id == current_merchant.id,
            Store.verification_status
            == StoreVerificationStatus.verified.value,
        )
        .order_by(
            (gross_sales - discounts).desc(),
            Offer.created_at.desc(),
        )
    ).all()

    gross_total = int(totals[0])
    discount_total = int(totals[1])
    offer_dashboard = MerchantOfferDashboard(
        gross_sales_paise=gross_total,
        discounts_paise=discount_total,
        net_sales_paise=gross_total - discount_total,
        sales_count=int(totals[2]),
        offers=[
            MerchantOfferPerformance(
                offer_id=offer.id,
                title=offer.title,
                status=offer.status,
                starts_at=offer.starts_at,
                ends_at=offer.ends_at,
                sales_count=int(sales_count),
                gross_sales_paise=int(offer_gross),
                discounts_paise=int(offer_discounts),
                net_sales_paise=int(offer_gross) - int(offer_discounts),
                vouchers_claimed=int(vouchers_claimed),
                vouchers_used=int(vouchers_used),
            )
            for (
                offer,
                offer_gross,
                offer_discounts,
                sales_count,
                vouchers_claimed,
                vouchers_used,
            ) in offer_rows
        ],
    )
    return MerchantDashboardResponse(
        billing=billing_dashboard,
        offer_analytics=offer_dashboard,
    )


@admin_dashboard_router.get(
    "/dashboard",
    response_model=AdminDashboardResponse,
    summary="Get platform offer and voucher performance without sales data",
)
def get_admin_dashboard(
    current_admin: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
    offers_limit: int = Query(default=50, ge=1, le=100),
    offers_offset: int = Query(default=0, ge=0),
) -> AdminDashboardResponse:
    merchant_totals = db.execute(
        select(
            func.count(User.id),
            func.coalesce(
                func.sum(case((User.is_active.is_(True), 1), else_=0)), 0
            ),
        ).where(User.role == UserRole.merchant.value)
    ).one()

    status_rows = db.execute(
        select(Offer.status, func.count(Offer.id))
        .group_by(Offer.status)
    ).all()
    offers_by_status = {offer_status: int(count) for offer_status, count in status_rows}
    offers_total = sum(offers_by_status.values())
    offers_published = offers_total - offers_by_status.get(
        OfferStatus.draft.value, 0
    )

    voucher_totals = db.execute(
        select(
            func.count(Voucher.id),
            func.coalesce(
                func.sum(
                    case(
                        (Voucher.status == VoucherStatus.redeemed.value, 1),
                        else_=0,
                    )
                ),
                0,
            ),
        )
    ).one()

    voucher_metrics = (
        select(
            Voucher.offer_id.label("offer_id"),
            func.count(Voucher.id).label("vouchers_claimed"),
            func.coalesce(
                func.sum(
                    case(
                        (Voucher.status == VoucherStatus.redeemed.value, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("vouchers_used"),
        )
        .group_by(Voucher.offer_id)
        .subquery()
    )
    offer_rows_query = (
        select(
            Offer,
            Store,
            User,
            func.coalesce(voucher_metrics.c.vouchers_claimed, 0),
            func.coalesce(voucher_metrics.c.vouchers_used, 0),
        )
        .join(Store, Offer.store_id == Store.id)
        .join(User, Store.owner_user_id == User.id)
        .outerjoin(voucher_metrics, voucher_metrics.c.offer_id == Offer.id)
    )
    offer_performance_order = (
        func.coalesce(voucher_metrics.c.vouchers_used, 0).desc(),
        func.coalesce(voucher_metrics.c.vouchers_claimed, 0).desc(),
        Offer.created_at.desc(),
    )
    top_offer_rows = db.execute(
        offer_rows_query.order_by(*offer_performance_order).limit(10)
    ).all()
    page_offer_rows = db.execute(
        offer_rows_query.order_by(*offer_performance_order)
        .limit(offers_limit)
        .offset(offers_offset)
    ).all()

    def offer_performance(row) -> AdminOfferPerformance:
        offer, store, merchant, claims, used = row
        return AdminOfferPerformance(
            offer_id=offer.id,
            title=offer.title,
            status=offer.status,
            published=offer.status != OfferStatus.draft.value,
            merchant_id=merchant.id,
            merchant_name=merchant.name,
            store_id=store.id,
            store_name=store.name,
            vouchers_claimed=int(claims),
            vouchers_used=int(used),
        )

    merchant_rows = db.execute(
        select(
            User,
            func.count(func.distinct(Offer.id)),
            func.count(
                func.distinct(
                    case(
                        (
                            Offer.status != OfferStatus.draft.value,
                            Offer.id,
                        ),
                        else_=None,
                    )
                )
            ),
            func.count(Voucher.id),
            func.coalesce(
                func.sum(
                    case(
                        (Voucher.status == VoucherStatus.redeemed.value, 1),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .outerjoin(Store, Store.owner_user_id == User.id)
        .outerjoin(Offer, Offer.store_id == Store.id)
        .outerjoin(Voucher, Voucher.offer_id == Offer.id)
        .where(User.role == UserRole.merchant.value)
        .group_by(User.id)
        .order_by(
            func.coalesce(
                func.sum(
                    case(
                        (Voucher.status == VoucherStatus.redeemed.value, 1),
                        else_=0,
                    )
                ),
                0,
            ).desc(),
            func.count(Voucher.id).desc(),
            User.created_at.desc(),
        )
        .limit(10)
    ).all()

    return AdminDashboardResponse(
        merchants_total=int(merchant_totals[0]),
        merchants_active=int(merchant_totals[1]),
        offers_total=offers_total,
        offers_published=offers_published,
        offers_by_status=offers_by_status,
        vouchers_claimed=int(voucher_totals[0]),
        vouchers_used=int(voucher_totals[1]),
        top_offers=[offer_performance(row) for row in top_offer_rows],
        offers=[offer_performance(row) for row in page_offer_rows],
        merchants_by_performance=[
            AdminMerchantPerformance(
                merchant_id=merchant.id,
                merchant_name=merchant.name,
                is_active=merchant.is_active,
                offers_created=int(offers_created),
                offers_published=int(offers_published_count),
                vouchers_claimed=int(vouchers_claimed),
                vouchers_used=int(vouchers_used),
            )
            for (
                merchant,
                offers_created,
                offers_published_count,
                vouchers_claimed,
                vouchers_used,
            ) in merchant_rows
        ],
        offers_offset=offers_offset,
        offers_limit=offers_limit,
    )
