"""Seed common Indian offline-store categories.

Revision ID: 20261026_categories
Revises: 20261026_maps
Create Date: 2026-10-26
"""
from typing import Sequence, Union
from uuid import NAMESPACE_URL, uuid5

from alembic import op
from sqlalchemy import String, column, table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.dialects.postgresql import UUID


revision: str = "20261026_categories"
down_revision: Union[str, Sequence[str], None] = "20261026_maps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORY_NAMES = (
    "Food & Dining / Vegetarian / Restaurant",
    "Food & Dining / Non-Vegetarian / Restaurant",
    "Food & Dining / Both Vegetarian & Non-Vegetarian / Restaurant",
    "Food & Dining / Vegetarian / Cafe",
    "Food & Dining / Non-Vegetarian / Cafe",
    "Food & Dining / Both Vegetarian & Non-Vegetarian / Cafe",
    "Food & Dining / Vegetarian / Fast Food",
    "Food & Dining / Non-Vegetarian / Fast Food",
    "Food & Dining / Both Vegetarian & Non-Vegetarian / Fast Food",
    "Food & Dining / Vegetarian / Bakery",
    "Food & Dining / Vegetarian / Sweet Shop",
    "Food & Dining / Vegetarian / Snacks & Chaat",
    "Food & Dining / Non-Vegetarian / Meat & Seafood Shop",
    "Food & Dining / Non-Vegetarian / Butcher",
    "Food & Dining / Both Vegetarian & Non-Vegetarian / Food Court",
    "Food & Dining / Vegetarian / Juice & Beverage Shop",
    "Food & Dining / Vegetarian / Ice Cream & Dessert Shop",
    "Grocery & Essentials / Kirana & General Store",
    "Grocery & Essentials / Supermarket",
    "Grocery & Essentials / Hypermarket",
    "Grocery & Essentials / Organic & Natural Foods",
    "Grocery & Essentials / Fruits & Vegetables",
    "Grocery & Essentials / Dairy & Milk Products",
    "Grocery & Essentials / Meat & Poultry",
    "Grocery & Essentials / Fish & Seafood",
    "Grocery & Essentials / Packaged Foods",
    "Grocery & Essentials / Water & Beverages",
    "Fashion & Apparel / Clothing",
    "Fashion & Apparel / Footwear",
    "Fashion & Apparel / Bags & Luggage",
    "Fashion & Apparel / Jewellery",
    "Fashion & Apparel / Watches & Accessories",
    "Fashion & Apparel / Tailoring & Alterations",
    "Beauty & Personal Care / Salon",
    "Beauty & Personal Care / Spa & Wellness",
    "Beauty & Personal Care / Cosmetics",
    "Beauty & Personal Care / Pharmacy & Personal Care",
    "Health & Medical / Pharmacy",
    "Health & Medical / Clinic",
    "Health & Medical / Dental Clinic",
    "Health & Medical / Optical & Eyewear",
    "Health & Medical / Diagnostic Laboratory",
    "Home & Living / Furniture",
    "Home & Living / Home Decor",
    "Home & Living / Kitchenware & Utensils",
    "Home & Living / Hardware & Building Materials",
    "Home & Living / Electrical & Lighting",
    "Home & Living / Plumbing Supplies",
    "Home & Living / Paint & Wallpaper",
    "Home & Living / Home Appliances",
    "Electronics & Technology / Mobile Phones & Accessories",
    "Electronics & Technology / Computers & Laptops",
    "Electronics & Technology / Consumer Electronics",
    "Electronics & Technology / Repair & Service",
    "Books, Gifts & Stationery / Bookstore",
    "Books, Gifts & Stationery / Stationery & Office Supplies",
    "Books, Gifts & Stationery / Gifts & Toys",
    "Books, Gifts & Stationery / Florist",
    "Automotive / Car Sales & Accessories",
    "Automotive / Motorcycle Sales & Accessories",
    "Automotive / Auto Repair & Service",
    "Automotive / Tyres & Batteries",
    "Automotive / Fuel Station",
    "Services / Laundry & Dry Cleaning",
    "Services / Courier & Parcel",
    "Services / Mobile & Electronics Repair",
    "Services / Photography & Printing",
    "Services / Travel Agency",
    "Services / Pet Shop & Veterinary",
    "Services / Education & Coaching",
    "Services / Fitness & Sports",
    "Services / Other Local Service",
    "Other / Other Local Shop",
)


def upgrade() -> None:
    categories = table(
        "store_categories",
        column("id", UUID(as_uuid=True)),
        column("name", String(length=100)),
    )
    values = [
        {
            "id": uuid5(NAMESPACE_URL, f"o2o-campaigner/store-category/{name}"),
            "name": name,
        }
        for name in CATEGORY_NAMES
    ]
    statement = insert(categories).values(values)
    statement = statement.on_conflict_do_nothing(index_elements=["name"])
    op.get_bind().execute(statement)


def downgrade() -> None:
    categories = table(
        "store_categories",
        column("id", UUID(as_uuid=True)),
        column("name", String(length=100)),
    )
    ids = [
        uuid5(NAMESPACE_URL, f"o2o-campaigner/store-category/{name}")
        for name in CATEGORY_NAMES
    ]
    op.get_bind().execute(
        categories.delete().where(categories.c.id.in_(ids))
    )
