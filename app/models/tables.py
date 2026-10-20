
import uuid
from decimal import Decimal
from sqlalchemy import (
    Boolean,
    String,
    Text,
    DateTime,
    ForeignKey,
    Numeric,
    Integer,
    BigInteger,
    CheckConstraint,
    Index,
    text,
    Date,
    UniqueConstraint,
)
from datetime import date
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import Mapped, mapped_column
from typing import Any
from app.db.session import Base

analytics_event_type_enum = ENUM(
    "impression",
    "view",
    "claim",
    name="analytics_event_type",
    schema="public",
    create_type=False,
)

sales_data_source_enum = ENUM(
    "merchant_entered",
    "simulated_demo",
    name="sales_data_source",
    schema="public",
    create_type=False,
)

redemption_source_enum = ENUM(
    "merchant_entered",
    "simulated",
    name="redemption_source",
    schema="public",
    create_type=False,
)

voucher_status_enum = ENUM(
    "claimed",
    "redeemed",
    "expired",
    "cancelled",
    name="voucher_status",
    schema="public",
    create_type=False,
)

offer_type_enum = ENUM(
    "percent",
    "fixed",
    name="offer_type",
    schema="public",
    create_type=False,
)

offer_status_enum = ENUM(
    "draft",
    "scheduled",
    "active",
    "paused",
    "expired",
    "cancelled",
    name="offer_status",
    schema="public",
    create_type=False,
)

store_verification_enum = ENUM(
    "pending",
    "verified",
    "rejected",
    "suspended",
    name="store_verification_status",
    schema="public",
    create_type=False,
)

user_role_enum = ENUM(
    "customer",
    "merchant",
    "admin",
    name="user_role",
    schema="public",
    create_type=False,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        user_role_enum,
        nullable=False,
        server_default=text("'customer'::public.user_role"),
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    prefs: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class StoreCategory(Base):
    __tablename__ = "store_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("store_categories.id", ondelete="RESTRICT"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    lng: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)

    hours: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    verification_status: Mapped[str] = mapped_column(
        store_verification_enum,
        nullable=False,
        server_default=text(
            "'pending'::public.store_verification_status"
        ),
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    
    __table_args__ = (
        Index("idx_stores_category", "category_id"),
        Index("idx_stores_lat_lng", "lat", "lng"),
        Index("idx_stores_owner", "owner_user_id"),
        Index("idx_stores_verification", "verification_status"),
    )
    
    

class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Database column is named "type"
    type: Mapped[str] = mapped_column(
        offer_type_enum,
        nullable=False,
    )

    value: Mapped[int] = mapped_column(Integer, nullable=False)

    min_order_paise: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )

    max_discount_paise: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    starts_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    ends_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        offer_status_enum,
        nullable=False,
        server_default=text("'draft'::public.offer_status"),
    )

    max_claims: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    per_customer_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    terms: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index("idx_offers_store_status", "store_id", "status"),
        Index("idx_offers_status_ends", "status", "ends_at"),
        CheckConstraint(
            "ends_at > starts_at",
            name="chk_offer_dates",
        ),
        CheckConstraint(
            "value > 0",
            name="offers_value_check",
        ),
        CheckConstraint(
            "max_claims IS NULL OR max_claims > 0",
            name="offers_max_claims_check",
        ),
        CheckConstraint(
            "max_discount_paise IS NULL OR max_discount_paise > 0",
            name="offers_max_discount_paise_check",
        ),
        CheckConstraint(
            "min_order_paise >= 0",
            name="offers_min_order_paise_check",
        ),
        CheckConstraint(
            "per_customer_limit > 0",
            name="offers_per_customer_limit_check",
        ),
        CheckConstraint(
            "version > 0",
            name="offers_version_check",
        ),
        CheckConstraint(
            "type <> 'percent'::public.offer_type "
            "OR (value >= 1 AND value <= 70)",
            name="chk_percent_range",
        ),
        CheckConstraint(
            "type <> 'fixed'::public.offer_type "
            "OR (value::bigint * 100) < min_order_paise "
            "OR min_order_paise = 0",
            name="chk_fixed_less_than_minimum",
        ),
    )
    
class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        voucher_status_enum,
        nullable=False,
        server_default=text("'claimed'::public.voucher_status"),
    )

    terms_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    claimed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    expires_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    redeemed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "idx_vouchers_customer_status",
            "customer_id",
            "status",
        ),
        Index(
            "idx_vouchers_expiry",
            "expires_at",
        ),
        Index(
            "idx_vouchers_store_status",
            "store_id",
            "status",
        ),
        CheckConstraint(
            "expires_at > claimed_at",
            name="chk_voucher_expiry",
        ),
        CheckConstraint(
            "(status = 'redeemed'::public.voucher_status "
            "AND redeemed_at IS NOT NULL) "
            "OR (status <> 'redeemed'::public.voucher_status "
            "AND redeemed_at IS NULL)",
            name="chk_redeemed_timestamp",
        ),
        # Matches the existing database's unique constraint.
        # This currently allows only one voucher per offer/customer.
        __import__("sqlalchemy").UniqueConstraint(
            "offer_id",
            "customer_id",
            name="uq_voucher_offer_customer",
        ),
    )
    
class VoucherRedemption(Base):
    __tablename__ = "voucher_redemptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    voucher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vouchers.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
    )

    redeemed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    bill_amount_paise: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    discount_paise: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        redemption_source_enum,
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index(
            "idx_redemptions_store",
            "store_id",
            "created_at",
        ),
        CheckConstraint(
            "bill_amount_paise IS NULL OR bill_amount_paise >= 0",
            name="voucher_redemptions_bill_amount_paise_check",
        ),
        CheckConstraint(
            "discount_paise >= 0",
            name="voucher_redemptions_discount_paise_check",
        ),
    )
    
class SalesTransaction(Base):
    __tablename__ = "sales_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
    )

    offer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="RESTRICT"),
        nullable=True,
    )

    voucher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vouchers.id", ondelete="RESTRICT"),
        nullable=True,
    )

    gross_amount_paise: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    discount_paise: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )

    cogs_paise: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    other_var_cost_paise: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    occurred_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    data_source: Mapped[str] = mapped_column(
        sales_data_source_enum,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_sales_offer", "offer_id"),
        Index("idx_sales_store_time", "store_id", "occurred_at"),
        Index("idx_sales_voucher", "voucher_id"),
        CheckConstraint(
            "gross_amount_paise >= 0",
            name="sales_transactions_gross_amount_paise_check",
        ),
        CheckConstraint(
            "discount_paise >= 0",
            name="sales_transactions_discount_paise_check",
        ),
        CheckConstraint(
            "cogs_paise IS NULL OR cogs_paise >= 0",
            name="sales_transactions_cogs_paise_check",
        ),
        CheckConstraint(
            "other_var_cost_paise IS NULL OR other_var_cost_paise >= 0",
            name="sales_transactions_other_var_cost_paise_check",
        ),
    )

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
    )

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        analytics_event_type_enum,
        nullable=False,
    )

    customer_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index(
            "idx_analytics_offer_event_time",
            "offer_id",
            "event_type",
            "created_at",
        ),
        Index(
            "idx_analytics_store_time",
            "store_id",
            "created_at",
        ),
    )
    
class CampaignExpense(Base):
    __tablename__ = "campaign_expenses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False
    )

    offer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="RESTRICT"),
        nullable=True
    )

    amount_paise: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    incurred_on: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE")
    )

    __table_args__ = (
        CheckConstraint(
            "amount_paise >= 0",
            name="campaign_expenses_amount_paise_check"
        ),
        Index("idx_campaign_expenses_store", "store_id"),
    )

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index("idx_notifications_expiry", "expires_at"),
        Index(
            "idx_notifications_user_created",
            "user_id",
            text("created_at DESC"),
        ),
        UniqueConstraint(
            "user_id",
            "offer_id",
            name="uq_notification_user_offer",
        ),
    )
    
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index("idx_audit_actor_time", "actor_user_id", "created_at"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )