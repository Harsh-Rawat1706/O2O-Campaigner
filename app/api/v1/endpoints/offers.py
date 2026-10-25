from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import require_roles
from app.db.dependencies import get_db
from app.models.enums import (
    OfferStatus,
    StoreVerificationStatus,
    UserRole,
    VoucherStatus,
)
from app.models.tables import AuditLog, Offer, Store, User, Voucher
from app.schemas.offer import OfferCreate, OfferResponse

router = APIRouter(prefix="/merchant/offers", tags=["Merchant Offers"])


@router.get(
    "",
    response_model=list[OfferResponse],
)
def list_merchant_offers(
    current_user: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> list[Offer]:
    statement = (
        select(Offer)
        .join(Store, Offer.store_id == Store.id)
        .where(Store.owner_user_id == current_user.id)
        .order_by(Offer.created_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post(
    "",
    response_model=OfferResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_offer(
    offer_data: OfferCreate,
    current_user: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> Offer:
    store = db.get(Store, offer_data.store_id)
    if store is None or store.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    if store.verification_status != StoreVerificationStatus.verified.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Offers can only be created for verified stores",
        )

    offer = Offer(
        store_id=store.id,
        title=offer_data.title,
        description=offer_data.description,
        type=offer_data.type,
        value=offer_data.value,
        min_order_paise=offer_data.min_order_paise,
        max_discount_paise=offer_data.max_discount_paise,
        starts_at=offer_data.starts_at,
        ends_at=offer_data.ends_at,
        status="draft",
        max_claims=offer_data.max_claims,
        per_customer_limit=offer_data.per_customer_limit,
        terms=offer_data.terms,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.delete(
    "/{offer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_offer(
    offer_id: UUID,
    current_user: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> Response:
    offer = db.scalar(
        select(Offer)
        .join(Store, Offer.store_id == Store.id)
        .where(
            Offer.id == offer_id,
            Store.owner_user_id == current_user.id,
        )
    )
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found",
        )

    if offer.status in {
        OfferStatus.cancelled.value,
        OfferStatus.expired.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Offer is already {offer.status}",
        )

    previous_status = offer.status
    try:
        offer.status = OfferStatus.cancelled.value
        db.execute(
            update(Voucher)
            .where(
                Voucher.offer_id == offer.id,
                Voucher.status == VoucherStatus.claimed.value,
            )
            .values(status=VoucherStatus.cancelled.value)
        )
        db.add(
            AuditLog(
                actor_user_id=current_user.id,
                action="offer_cancelled",
                entity_type="offer",
                entity_id=offer.id,
                metadata_={"previous_status": previous_status},
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)
