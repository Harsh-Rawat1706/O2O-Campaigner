from datetime import datetime, timezone
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import require_roles
from app.db.dependencies import get_db
from app.models.enums import OfferStatus, StoreVerificationStatus, UserRole
from app.models.tables import Offer, Store, User, Voucher
from app.schemas.customer import (
    CustomerOfferResponse,
    CustomerStoreSummary,
    CustomerVoucherDetailResponse,
    CustomerVoucherResponse,
)
from app.schemas.customer_dashboard import CustomerVoucherDashboardResponse

router = APIRouter(prefix="/customer", tags=["Customer"])


@router.get("/offers", response_model=list[CustomerOfferResponse])
def list_customer_offers(
    current_user: User = Depends(require_roles(UserRole.customer)),
    db: Session = Depends(get_db),
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=2, ge=2, le=10),
    category_id: UUID | None = Query(
        default=None,
        description="Optional store category UUID. Omit it to include every category.",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[CustomerOfferResponse]:
    now = datetime.now(timezone.utc)
    latitude_radians = func.radians(latitude)
    store_latitude_radians = func.radians(Store.lat)
    cosine_of_distance = (
        func.sin(latitude_radians) * func.sin(store_latitude_radians)
        + func.cos(latitude_radians)
        * func.cos(store_latitude_radians)
        * func.cos(func.radians(Store.lng - longitude))
    )
    distance_km = (
        func.acos(func.least(1.0, func.greatest(-1.0, cosine_of_distance)))
        * 6371.0088
    ).label("distance_km")

    statement = (
        select(Offer, Store, distance_km)
        .join(Store, Offer.store_id == Store.id)
        .where(
            Offer.status == OfferStatus.active.value,
            Offer.starts_at <= now,
            Offer.ends_at > now,
            Store.verification_status == StoreVerificationStatus.verified.value,
            distance_km <= radius_km,
        )
        .order_by(distance_km.asc(), Offer.ends_at.asc())
        .limit(limit)
        .offset(offset)
    )
    if category_id is not None:
        statement = statement.where(Store.category_id == category_id)
    rows = db.execute(statement).all()

    return [
        CustomerOfferResponse(
            id=offer.id,
            title=offer.title,
            description=offer.description,
            type=offer.type,
            value=offer.value,
            min_order_paise=offer.min_order_paise,
            max_discount_paise=offer.max_discount_paise,
            starts_at=offer.starts_at,
            ends_at=offer.ends_at,
            store=CustomerStoreSummary(
                id=store.id,
                name=store.name,
                address=store.address,
                lat=store.lat,
                lng=store.lng,
                google_maps_link=store.google_maps_link,
                distance_km=float(distance),
            ),
        )
        for offer, store, distance in rows
    ]


@router.post(
    "/offers/{offer_id}/claim",
    response_model=CustomerVoucherResponse,
    status_code=status.HTTP_201_CREATED,
)
def claim_customer_offer(
    offer_id: UUID,
    current_user: User = Depends(require_roles(UserRole.customer)),
    db: Session = Depends(get_db),
) -> Voucher:
    offer = db.scalar(
        select(Offer).where(Offer.id == offer_id).with_for_update()
    )
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found",
        )

    now = datetime.now(timezone.utc)
    if (
        offer.status != OfferStatus.active.value
        or offer.starts_at > now
        or offer.ends_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Offer is not currently active",
        )

    store = db.get(Store, offer.store_id)
    if (
        store is None
        or store.verification_status
        != StoreVerificationStatus.verified.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Offer store is not verified",
        )

    existing_voucher = db.scalar(
        select(Voucher.id).where(
            Voucher.offer_id == offer.id,
            Voucher.customer_id == current_user.id,
        )
    )
    if existing_voucher is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already claimed this offer",
        )

    total_claims = db.scalar(
        select(func.count(Voucher.id)).where(Voucher.offer_id == offer.id)
    )
    if offer.max_claims is not None and total_claims >= offer.max_claims:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Offer has reached its claim limit",
        )

    voucher = Voucher(
        code=secrets.token_urlsafe(16),
        offer_id=offer.id,
        store_id=offer.store_id,
        customer_id=current_user.id,
        status="claimed",
        terms_snapshot={
            "title": offer.title,
            "type": offer.type,
            "value": offer.value,
            "min_order_paise": offer.min_order_paise,
            "max_discount_paise": offer.max_discount_paise,
            "terms": offer.terms,
        },
        expires_at=offer.ends_at,
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return voucher


@router.get("/vouchers", response_model=list[CustomerVoucherDetailResponse])
def list_customer_vouchers(
    current_user: User = Depends(require_roles(UserRole.customer)),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[CustomerVoucherDetailResponse]:
    rows = db.execute(
        select(Voucher, Offer, Store)
        .join(Offer, Voucher.offer_id == Offer.id)
        .join(Store, Voucher.store_id == Store.id)
        .where(Voucher.customer_id == current_user.id)
        .order_by(Voucher.claimed_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return [
        CustomerVoucherDetailResponse(
            id=voucher.id,
            code=voucher.code,
            offer_id=voucher.offer_id,
            store_id=voucher.store_id,
            status=voucher.status,
            claimed_at=voucher.claimed_at,
            expires_at=voucher.expires_at,
            offer_title=offer.title,
            store_name=store.name,
        )
        for voucher, offer, store in rows
    ]


@router.get(
    "/dashboard",
    response_model=CustomerVoucherDashboardResponse,
    summary="Get customer voucher usage totals",
)
def get_customer_dashboard(
    current_user: User = Depends(require_roles(UserRole.customer)),
    db: Session = Depends(get_db),
) -> CustomerVoucherDashboardResponse:
    rows = db.execute(
        select(Voucher.status, func.count(Voucher.id))
        .where(Voucher.customer_id == current_user.id)
        .group_by(Voucher.status)
    ).all()
    counts = {voucher_status: int(count) for voucher_status, count in rows}
    claimed = counts.get("claimed", 0)
    used = counts.get("redeemed", 0)
    expired = counts.get("expired", 0)
    cancelled = counts.get("cancelled", 0)
    return CustomerVoucherDashboardResponse(
        vouchers_claimed=claimed + used + expired + cancelled,
        vouchers_used=used,
        vouchers_available=claimed,
        vouchers_expired=expired,
        vouchers_cancelled=cancelled,
    )
