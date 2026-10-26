
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine

from app.db.session import Base, DATABASE_URL as APP_DATABASE_URL
from app.models import *

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is missing from .env")

DATABASE_URL = APP_DATABASE_URL
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def compare_type(context, inspected_column, metadata_column,
                 inspected_type, metadata_type):

    # PostgreSQL ENUMs ko name aur values ke basis par compare karo.
    if (
        getattr(inspected_type, "name", None)
        and getattr(metadata_type, "name", None)
        and inspected_type.__class__.__name__ == "ENUM"
        and metadata_type.__class__.__name__ == "ENUM"
    ):
        return (
            inspected_type.name != metadata_type.name
            or tuple(inspected_type.enums) != tuple(metadata_type.enums)
        )

    return None

def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(DATABASE_URL, pool_pre_ping=True)

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=compare_type,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
