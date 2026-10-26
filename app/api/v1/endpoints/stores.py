from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased

from app.api.v1.endpoints.auth import require_roles
from app.db.dependencies import get_db
from app.models.enums import StoreVerificationStatus, UserRole
from app.models.tables import AuditLog, Store, StoreCategory, User
from app.schemas.admin import DeletedStoreResponse, StoreRestorationResponse
from app.schemas.store import (
    StoreCreate,
    StoreCategoryResponse,
    StoreResponse,
    StoreVerificationRequest,
)

router = APIRouter(prefix="/merchant/stores")
admin_router = APIRouter(prefix="/admin/stores")


@admin_router.get(
    "/pending",
    response_model=list[StoreResponse],
    summary="List stores pending verification",
)
def list_pending_stores(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[Store]:
    statement = (
        select(Store)
        .where(
            Store.verification_status == StoreVerificationStatus.pending.value
        )
        .order_by(Store.created_at.asc(), Store.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())


@router.get(
    "/categories",
    response_model=list[StoreCategoryResponse],
    summary="List available store categories",
)
def list_store_categories(
    db: Session = Depends(get_db),
) -> list[StoreCategory]:
    return list(
        db.scalars(select(StoreCategory).order_by(StoreCategory.name.asc())).all()
    )


def _latest_store_archive_event_id():
    return (
        select(AuditLog.id)
        .where(
            AuditLog.entity_type == "store",
            AuditLog.entity_id == Store.id,
            AuditLog.action.in_(("store_deleted", "store_restored")),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(1)
        .correlate(Store)
        .scalar_subquery()
    )


def _soft_delete_store(
    store_id: UUID,
    actor: User,
    db: Session,
    owner_user_id: UUID | None = None,
) -> Response:
    statement = select(Store).where(Store.id == store_id)
    if owner_user_id is not None:
        statement = statement.where(Store.owner_user_id == owner_user_id)
    store = db.scalar(statement.with_for_update())
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    latest_archive_event = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.entity_type == "store",
            AuditLog.entity_id == store.id,
            AuditLog.action.in_(("store_deleted", "store_restored")),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(1)
    )
    if (
        latest_archive_event is not None
        and latest_archive_event.action == "store_deleted"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Store is already deleted",
        )

    previous_status = store.verification_status
    store.verification_status = StoreVerificationStatus.suspended.value
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            action="store_deleted",
            entity_type="store",
            entity_id=store.id,
            metadata_={
                "reason": "merchant_request"
                if owner_user_id is not None
                else "admin_request",
                "previous_status": previous_status,
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        .where(
            Store.owner_user_id == current_user.id,
            ~exists().where(
                AuditLog.id == _latest_store_archive_event_id(),
                AuditLog.action == "store_deleted",
            ),
        )
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
    category_id = store_data.category_id
    if store_data.category_name is not None:
        category = db.scalar(
            select(StoreCategory).where(
                func.lower(StoreCategory.name)
                == store_data.category_name.lower()
            )
        )
        category_id = category.id if category is not None else None
    elif category_id is not None:
        category = db.get(StoreCategory, category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store category not found",
            )

    store = Store(
        owner_user_id=current_user.id,
        category_id=category_id,
        name=store_data.name,
        address=store_data.address,
        lat=store_data.lat,
        lng=store_data.lng,
        google_maps_link=store_data.google_maps_link,
        hours=store_data.hours,
        phone=store_data.phone,
        verification_status="pending",
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one of your stores",
    description=(
        "Soft-deletes the store by suspending it and retaining its records."
    ),
)
def delete_merchant_store(
    store_id: UUID,
    current_user: User = Depends(require_roles(UserRole.merchant)),
    db: Session = Depends(get_db),
) -> Response:
    return _soft_delete_store(
        store_id,
        actor=current_user,
        db=db,
        owner_user_id=current_user.id,
    )


@admin_router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete any store",
    description=(
        "Soft-deletes the store by suspending it and retaining its records."
    ),
)
def delete_store_as_admin(
    store_id: UUID,
    current_admin: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> Response:
    return _soft_delete_store(store_id, actor=current_admin, db=db)


@admin_router.get(
    "/deleted",
    response_model=list[DeletedStoreResponse],
    summary="List retained deleted stores",
)
def list_deleted_stores(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[DeletedStoreResponse]:
    latest_event = aliased(AuditLog)
    statement = (
        select(Store, latest_event)
        .join(latest_event, latest_event.id == _latest_store_archive_event_id())
        .where(latest_event.action == "store_deleted")
        .order_by(latest_event.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(statement).all()
    return [
        DeletedStoreResponse(
            id=store.id,
            owner_user_id=store.owner_user_id,
            category_id=store.category_id,
            name=store.name,
            address=store.address,
            lat=store.lat,
            lng=store.lng,
            google_maps_link=store.google_maps_link,
            hours=store.hours,
            phone=store.phone,
            verification_status=store.verification_status,
            created_at=store.created_at,
            deleted_at=event.created_at,
            deleted_by=event.actor_user_id,
            deletion_reason=event.metadata_.get("reason"),
        )
        for store, event in rows
    ]


@admin_router.post(
    "/{store_id}/restore",
    response_model=StoreRestorationResponse,
)
def restore_store(
    store_id: UUID,
    current_admin: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> StoreRestorationResponse:
    store = db.scalar(
        select(Store).where(Store.id == store_id).with_for_update()
    )
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    latest_archive_event = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.entity_type == "store",
            AuditLog.entity_id == store.id,
            AuditLog.action.in_(("store_deleted", "store_restored")),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(1)
    )
    if (
        latest_archive_event is None
        or latest_archive_event.action != "store_deleted"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Store is not deleted",
        )

    owner = db.get(User, store.owner_user_id)
    if owner is None or not owner.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reactivate the store owner before restoring this store",
        )

    previous_status = latest_archive_event.metadata_.get("previous_status")
    allowed_statuses = {item.value for item in StoreVerificationStatus}
    if previous_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Store's previous status is unavailable; manual review required",
        )

    store.verification_status = previous_status
    db.add(
        AuditLog(
            actor_user_id=current_admin.id,
            action="store_restored",
            entity_type="store",
            entity_id=store.id,
            metadata_={
                "previous_status": StoreVerificationStatus.suspended.value,
                "new_status": previous_status,
                "restored_from_deletion": True,
            },
        )
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return StoreRestorationResponse(
        id=store.id,
        name=store.name,
        owner_user_id=store.owner_user_id,
        verification_status=store.verification_status,
        records_retained=True,
    )


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
