from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import require_roles
from app.db.dependencies import get_db
from app.models.enums import StoreVerificationStatus, UserRole
from app.models.tables import AuditLog, Store, User
from app.schemas.admin import (
    MerchantDeactivationResponse,
    MerchantRestorationResponse,
)
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/merchants", response_model=list[UserResponse])
def list_merchants(
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[User]:
    statement = select(User).where(User.role == UserRole.merchant.value)
    if is_active is not None:
        statement = statement.where(User.is_active.is_(is_active))
    statement = statement.order_by(User.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.delete(
    "/merchants/{merchant_id}",
    response_model=MerchantDeactivationResponse,
)
def deactivate_merchant(
    merchant_id: UUID,
    current_admin: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> MerchantDeactivationResponse:
    merchant = db.scalar(
        select(User).where(User.id == merchant_id).with_for_update()
    )
    if merchant is None or merchant.role != UserRole.merchant.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found",
        )
    if not merchant.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Merchant is already deactivated",
        )

    stores = list(
        db.scalars(
            select(Store)
            .where(Store.owner_user_id == merchant.id)
            .with_for_update()
        ).all()
    )
    previous_active = merchant.is_active
    previous_store_statuses = {
        str(store.id): store.verification_status for store in stores
    }
    store_ids = [store.id for store in stores]
    latest_store_actions: dict[UUID, str] = {}
    if store_ids:
        events = db.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "store",
                AuditLog.action.in_(("store_deleted", "store_restored")),
                AuditLog.entity_id.in_(store_ids),
            )
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        ).all()
        for event in events:
            if event.entity_id not in latest_store_actions:
                latest_store_actions[event.entity_id] = event.action
    previously_deleted_store_ids = {
        store_id
        for store_id, action in latest_store_actions.items()
        if action == "store_deleted"
    }

    merchant.is_active = False
    for store in stores:
        store.verification_status = StoreVerificationStatus.suspended.value

    db.add(
        AuditLog(
            actor_user_id=current_admin.id,
            action="merchant_deactivated",
            entity_type="user",
            entity_id=merchant.id,
            metadata_={
                "previous_is_active": previous_active,
                "email": merchant.email,
                "stores_suspended": len(stores),
                "records_retained": True,
            },
        )
    )
    for store in stores:
        if store.id in previously_deleted_store_ids:
            continue
        db.add(
            AuditLog(
                actor_user_id=current_admin.id,
                action="store_deleted",
                entity_type="store",
                entity_id=store.id,
                metadata_={
                    "reason": "merchant_deactivated",
                    "previous_status": previous_store_statuses[str(store.id)],
                    "new_status": StoreVerificationStatus.suspended.value,
                    "records_retained": True,
                },
            )
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return MerchantDeactivationResponse(
        id=merchant.id,
        name=merchant.name,
        email=merchant.email,
        is_active=merchant.is_active,
        stores_suspended=len(stores),
        records_retained=True,
    )


@router.post(
    "/merchants/{merchant_id}/restore",
    response_model=MerchantRestorationResponse,
)
def restore_merchant(
    merchant_id: UUID,
    current_admin: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> MerchantRestorationResponse:
    merchant = db.scalar(
        select(User).where(User.id == merchant_id).with_for_update()
    )
    if merchant is None or merchant.role != UserRole.merchant.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found",
        )
    if merchant.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Merchant is already active",
        )

    merchant.is_active = True
    db.add(
        AuditLog(
            actor_user_id=current_admin.id,
            action="merchant_restored",
            entity_type="user",
            entity_id=merchant.id,
            metadata_={"previous_is_active": False},
        )
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return MerchantRestorationResponse(
        id=merchant.id,
        name=merchant.name,
        email=merchant.email,
        is_active=merchant.is_active,
        stores_restored=False,
    )
