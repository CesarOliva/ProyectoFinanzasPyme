"""Conexión a la base de datos (SQLAlchemy Core)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.models import VISTA_VENTAS_DIARIAS, metadata


def crear_engine(url: str) -> Engine:
    if url in ("sqlite://", "sqlite:///:memory:"):
        # SQLite en memoria (pruebas): una sola conexión compartida para que la base persista.
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


@lru_cache
def get_engine() -> Engine:
    return crear_engine(get_settings().database_url)


def crear_esquema(engine: Engine) -> None:
    """Crea tablas y vista (usado en pruebas y en la migración inicial)."""
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP VIEW IF EXISTS v_ventas_diarias"))
        conn.execute(text(VISTA_VENTAS_DIARIAS))


def get_conn() -> Iterator[Connection]:
    """Dependencia de FastAPI: una conexión con transacción por petición."""
    with get_engine().begin() as conn:
        yield conn
