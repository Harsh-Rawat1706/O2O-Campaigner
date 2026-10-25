from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import require_roles
from app.db.dependencies import get_db
from app.models.enums import StoreVerificationStatus, UserRole
from app.models.tables import AuditLog, Store, StoreCategory, User
from app.schemas.store import (
    StoreCreate,
    StoreResponse,
    StoreVerificationRequest,
)

router = APIRouter(prefix="/merchant/stores")
admin_router = APIRouter(prefix="/admin/stores")


@router.get(
    "",
    response_model=list[StoreResponse],
)
def list_merchant_stores(
    current_user: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> list[Store]:
    statement = (
        select(Store)
        .where(Store.owner_user_id == current_user.id)
        .order_by(Store.created_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post(
    "",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_store(
    store_data: StoreCreate,
    current_user: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> Store:
    if store_data.category_id is not None:
        category = db.get(StoreCategory, store_data.category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store category not found",
            )

    store = Store(
        owner_user_id=current_user.id,
        category_id=store_data.category_id,
        name=store_data.name,
        address=store_data.address,
        lat=store_data.lat,
        lng=store_data.lng,
        hours=store_data.hours,
        phone=store_data.phone,
        verification_status="pending",
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@admin_router.patch(
    "/{store_id}/verification",
    response_model=StoreResponse,
)
def review_store(
    store_id: UUID,
    review: StoreVerificationRequest,
    current_user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    if store.verification_status != StoreVerificationStatus.pending.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending stores can be reviewed",
        )

    reason = review.reason.strip() if review.reason else None
    if review.decision == "reject" and not reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A reason is required when rejecting a store",
        )

    new_status = (
        StoreVerificationStatus.verified.value
        if review.decision == "approve"
        else StoreVerificationStatus.rejected.value
    )
    store.verification_status = new_status
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action=f"store_{review.decision}",
            entity_type="store",
            entity_id=store.id,
            metadata_={
                "reason": reason,
                "previous_status": StoreVerificationStatus.pending.value,
                "new_status": new_status,
            },
        )
    )
    db.commit()
    db.refresh(store)
    return store
