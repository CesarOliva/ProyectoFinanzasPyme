"""Dependencias de la API: usuario autenticado, permiso por empresa y periodo."""

from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Connection, select

from app.api.seguridad import leer_token
from app.db import models as m
from app.db.session import get_conn
from app.finance import consultas as q
from app.finance.periodos import fin_de_mes

Conn = Annotated[Connection, Depends(get_conn)]
_bearer = HTTPBearer(auto_error=False)


def usuario_actual(conn: Conn, credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if credenciales is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inicia sesión para continuar.")
    id_usuario = leer_token(credenciales.credentials)
    if id_usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tu sesión expiró. Vuelve a iniciar sesión.")
    usuario = conn.execute(select(m.usuarios.c.id_usuario, m.usuarios.c.nombre, m.usuarios.c.email)
                           .where(m.usuarios.c.id_usuario == id_usuario)).mappings().first()
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tu sesión no es válida.")
    return dict(usuario)


Usuario = Annotated[dict, Depends(usuario_actual)]


def empresa_autorizada(conn: Conn, usuario: Usuario, id_empresa: Annotated[int, Path(ge=1)]) -> int:
    """El id_empresa de la URL solo se acepta si el usuario autenticado tiene acceso (CLAUDE.md §8)."""
    permitido = conn.execute(select(m.usuarios_empresas.c.rol).where(
        m.usuarios_empresas.c.id_usuario == usuario["id_usuario"],
        m.usuarios_empresas.c.id_empresa == id_empresa,
    )).first()
    if permitido is None:
        # 404 y no 403: no revelamos si la empresa existe.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese negocio en tu cuenta.")
    return id_empresa


EmpresaId = Annotated[int, Depends(empresa_autorizada)]


def empresa_editable(conn: Conn, usuario: Usuario, id_empresa: EmpresaId) -> int:
    """Solo el dueño puede cambiar datos; el rol 'consulta' (p. ej. su contador) solo lee."""
    rol = conn.execute(select(m.usuarios_empresas.c.rol).where(
        m.usuarios_empresas.c.id_usuario == usuario["id_usuario"],
        m.usuarios_empresas.c.id_empresa == id_empresa,
    )).scalar()
    if rol != "dueno":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tienes acceso de solo lectura a este negocio.")
    return id_empresa


EmpresaEditable = Annotated[int, Depends(empresa_editable)]


def periodo(conn: Conn, id_empresa: EmpresaId, desde: date | None = Query(None), hasta: date | None = Query(None)) -> tuple[date, date]:
    """Si no se envía periodo, se usa el mes del último dato registrado."""
    if desde and hasta:
        if desde > hasta:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La fecha inicial es posterior a la final.")
        return desde, hasta
    corte = q.rango_datos(conn, id_empresa)[1] or date.today()
    return corte.replace(day=1), fin_de_mes(corte)


Periodo = Annotated[tuple[date, date], Depends(periodo)]
