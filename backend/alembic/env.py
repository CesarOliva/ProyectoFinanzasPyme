"""Entorno de Alembic: usa el mismo engine y metadata que la aplicación."""

from alembic import context

from app.db.models import metadata
from app.db.session import get_engine

target_metadata = metadata


def run_migrations_online() -> None:
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
