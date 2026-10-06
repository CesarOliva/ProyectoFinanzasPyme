"""Contraseñas (PBKDF2 de la biblioteca estándar) y tokens JWT."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings

_ITERACIONES = 240_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERACIONES)
    return f"pbkdf2_sha256${_ITERACIONES}${salt}${digest.hex()}"


def verificar_password(password: str, guardado: str) -> bool:
    try:
        _, iteraciones, salt, esperado = guardado.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iteraciones))
    return hmac.compare_digest(digest.hex(), esperado)


def crear_token(id_usuario: int) -> str:
    ajustes = get_settings()
    ahora = datetime.now(UTC)
    payload = {"sub": str(id_usuario), "iat": ahora, "exp": ahora + timedelta(hours=ajustes.jwt_expira_horas)}
    return jwt.encode(payload, ajustes.jwt_secret, algorithm="HS256")


def leer_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
