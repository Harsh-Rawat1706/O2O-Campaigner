"""Add merchant invoices and line items.

Revision ID: 20261026_invoices
Revises: 20261026_categories
Create Date: 2026-10-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261026_invoices"
down_revision: Union[str, Sequence[str], None] = "20261026_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voucher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subtotal_paise", sa.BigInteger(), nullable=False),
        sa.Column(
            "discount_paise",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("total_paise", sa.BigInteger(), nullable=False),
        sa.Column(
            "payment_status",
            sa.String(length=20),
            server_default=sa.text("'unpaid'"),
            nullable=False,
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "subtotal_paise >= 0",
            name="invoices_subtotal_check",
        ),
        sa.CheckConstraint(
            "discount_paise >= 0",
            name="invoices_discount_check",
        ),
        sa.CheckConstraint(
            "total_paise >= 0",
            name="invoices_total_check",
        ),
        sa.CheckConstraint(
            "discount_paise <= subtotal_paise",
            name="invoices_discount_within_subtotal_check",
        ),
        sa.CheckConstraint(
            "total_paise = subtotal_paise - discount_paise",
            name="invoices_total_matches_subtotal_check",
        ),
        sa.CheckConstraint(
            "payment_status IN ('paid', 'unpaid')",
            name="invoices_payment_status_check",
        ),
        sa.CheckConstraint(
            "(payment_status = 'paid' AND paid_at IS NOT NULL) "
            "OR (payment_status = 'unpaid' AND paid_at IS NULL)",
            name="invoices_paid_at_check",
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["users.id"],
            name="invoices_merchant_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="invoices_store_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["voucher_id"],
            ["vouchers.id"],
            name="invoices_voucher_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="invoices_pkey"),
        sa.UniqueConstraint("code", name="invoices_code_key"),
        sa.UniqueConstraint("voucher_id", name="invoices_voucher_id_key"),
    )
    op.create_index(
        "idx_invoices_merchant_issued",
        "invoices",
        ["merchant_id", "issued_at"],
    )
    op.create_index(
        "idx_invoices_store_issued",
        "invoices",
        ["store_id", "issued_at"],
    )

    op.create_table(
        "invoice_line_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_paise", sa.BigInteger(), nullable=False),
        sa.Column("line_total_paise", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0",
            name="invoice_line_items_quantity_check",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="invoice_line_items_position_check",
        ),
        sa.CheckConstraint(
            "unit_price_paise >= 0",
            name="invoice_line_items_unit_price_check",
        ),
        sa.CheckConstraint(
            "line_total_paise >= 0",
            name="invoice_line_items_total_check",
        ),
        sa.CheckConstraint(
            "line_total_paise = quantity * unit_price_paise",
            name="invoice_line_items_total_matches_check",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="invoice_line_items_invoice_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="invoice_line_items_pkey"),
        sa.UniqueConstraint(
            "invoice_id",
            "position",
            name="invoice_line_items_position_key",
        ),
    )
    op.create_index(
        "idx_invoice_line_items_invoice",
        "invoice_line_items",
        ["invoice_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_invoice_line_items_invoice",
        table_name="invoice_line_items",
    )
    op.drop_table("invoice_line_items")
    op.drop_index("idx_invoices_store_issued", table_name="invoices")
    op.drop_index("idx_invoices_merchant_issued", table_name="invoices")
    op.drop_table("invoices")
