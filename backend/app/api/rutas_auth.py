"""Registro, inicio de sesión y datos del usuario."""

from datetime import date

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import insert, select

from app.api.deps import Conn, Usuario
from app.api.seguridad import crear_token, hash_password, verificar_password
from app.db import models as m

router = APIRouter(prefix="/auth", tags=["auth"])


class Registro(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nombre_negocio: str = Field(min_length=2, max_length=150)
    giro: str = Field(min_length=2, max_length=80)
    ciudad: str | None = Field(None, max_length=80)
    saldo_inicial: float = Field(0, ge=0, le=100_000_000)


class Login(BaseModel):
    email: EmailStr
    password: str


class EmpresaResumen(BaseModel):
    id_empresa: int
    nombre_negocio: str
    giro: str
    ciudad: str | None
    rol: str


class Sesion(BaseModel):
    token: str
    usuario: dict
    empresas: list[EmpresaResumen]


def _empresas(conn, id_usuario: int) -> list[EmpresaResumen]:
    filas = conn.execute(
        select(m.empresas.c.id_empresa, m.empresas.c.nombre_negocio, m.empresas.c.giro, m.empresas.c.ciudad,
               m.usuarios_empresas.c.rol)
        .join(m.usuarios_empresas, m.usuarios_empresas.c.id_empresa == m.empresas.c.id_empresa)
        .where(m.usuarios_empresas.c.id_usuario == id_usuario)
        .order_by(m.empresas.c.nombre_negocio)
    ).mappings()
    return [EmpresaResumen(**f) for f in filas]


@router.post("/registro", response_model=Sesion, status_code=status.HTTP_201_CREATED)
def registro(datos: Registro, conn: Conn) -> Sesion:
    email = datos.email.lower()
    if conn.execute(select(m.usuarios.c.id_usuario).where(m.usuarios.c.email == email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese correo. Inicia sesión.")
    id_usuario = conn.execute(insert(m.usuarios).values(
        nombre=datos.nombre.strip(), email=email, password_hash=hash_password(datos.password))).inserted_primary_key[0]
    id_empresa = conn.execute(insert(m.empresas).values(
        nombre_negocio=datos.nombre_negocio.strip(), giro=datos.giro.strip(), ciudad=datos.ciudad,
        saldo_inicial=datos.saldo_inicial, fecha_saldo_inicial=date.today())).inserted_primary_key[0]
    conn.execute(insert(m.usuarios_empresas).values(id_usuario=id_usuario, id_empresa=id_empresa, rol="dueno"))
    return Sesion(token=crear_token(id_usuario), usuario={"id_usuario": id_usuario, "nombre": datos.nombre, "email": email},
                  empresas=_empresas(conn, id_usuario))


@router.post("/login", response_model=Sesion)
def login(datos: Login, conn: Conn) -> Sesion:
    fila = conn.execute(select(m.usuarios).where(m.usuarios.c.email == datos.email.lower())).mappings().first()
    if fila is None or not verificar_password(datos.password, fila["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos.")
    usuario = {"id_usuario": fila["id_usuario"], "nombre": fila["nombre"], "email": fila["email"]}
    return Sesion(token=crear_token(fila["id_usuario"]), usuario=usuario, empresas=_empresas(conn, fila["id_usuario"]))


@router.get("/yo")
def yo(conn: Conn, usuario: Usuario) -> dict:
    return {"usuario": usuario, "empresas": [e.model_dump() for e in _empresas(conn, usuario["id_usuario"])]}
