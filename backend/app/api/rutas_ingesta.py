"""Importación de Excel/CSV: analizar → previsualizar → confirmar, historial y deshacer."""

from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import Conn, EmpresaEditable, EmpresaId, Usuario
from app.config import get_settings
from app.ingestion import carga, limpieza, mapeo, plantillas
from app.ingestion.campos import TIPOS, campos_de, claves_de
from app.ingestion.lectura import ArchivoInvalido, leer_archivo, perfilar

router = APIRouter(tags=["importar"])
TipoDatos = Literal["ventas", "productos", "compras", "gastos"]


def _campos(tipo: str) -> list[dict]:
    return [{"clave": c.clave, "etiqueta": c.etiqueta, "requerido": c.requerido, "descripcion": c.descripcion,
             "ejemplo": c.ejemplo} for c in campos_de(tipo)]


@router.get("/importar/campos")
def campos() -> dict:
    return {tipo: _campos(tipo) for tipo in TIPOS}


@router.get("/importar/plantillas/{tipo}")
def plantilla(tipo: TipoDatos) -> Response:
    return Response(plantillas.generar(tipo),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="plantilla_{tipo}.xlsx"'})


@router.post("/empresas/{id_empresa}/importaciones/analizar")
def analizar(id_empresa: EmpresaEditable, usuario: Usuario, archivo: UploadFile = File(...),
             tipo_datos: TipoDatos = Form(...)) -> dict:
    # Endpoint síncrono: FastAPI lo corre en un hilo, así la llamada al LLM no bloquea el servidor.
    max_mb = get_settings().max_archivo_mb
    contenido = archivo.file.read(max_mb * 1024 * 1024 + 1)
    try:
        tabla = leer_archivo(archivo.filename or "archivo", contenido, max_mb)
    except ArchivoInvalido as error:
        raise HTTPException(400, str(error)) from error
    propuesta, uso_ia = mapeo.proponer(tipo_datos, tabla)
    token = carga.guardar_staging(tabla, id_empresa, usuario["id_usuario"], tipo_datos, archivo.filename or "archivo")
    return {
        "token": token, "tipo_datos": tipo_datos, "nombre_archivo": archivo.filename, "filas": len(tabla.filas),
        "fila_encabezado": tabla.fila_encabezado, "columnas": perfilar(tabla), "mapeo": propuesta,
        "campos": _campos(tipo_datos), "advertencias": tabla.advertencias, "uso_ia": uso_ia,
        "vista_previa": tabla.filas[:5],
    }


class MapeoEntrada(BaseModel):
    mapeo: dict[str, str | None]


def _procesar(token: str, id_empresa: int, entrada: MapeoEntrada) -> tuple[dict, limpieza.Resultado]:
    try:
        staging = carga.leer_staging(token, id_empresa)
    except carga.StagingNoEncontrado as error:
        raise HTTPException(404, "La carga expiró o no existe. Vuelve a subir el archivo.") from error
    tipo, tabla = staging["tipo"], staging["tabla"]
    validos = claves_de(tipo)
    elegido = {col: campo for col, campo in entrada.mapeo.items() if col in tabla.columnas and campo in validos}
    if len(set(elegido.values())) != len(elegido):
        raise HTTPException(422, "Asignaste el mismo campo a dos columnas.")
    faltan = mapeo.faltantes(tipo, elegido)
    if faltan:
        raise HTTPException(422, f"Falta indicar qué columna es: {', '.join(faltan)}.")
    return staging, limpieza.limpiar(tipo, tabla.columnas, tabla.filas, elegido, tabla.numeros)


def _vista(fila: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else str(v)) for k, v in fila.items()}


@router.post("/empresas/{id_empresa}/importaciones/{token}/previsualizar")
def previsualizar(token: str, entrada: MapeoEntrada, id_empresa: EmpresaEditable) -> dict:
    _, resultado = _procesar(token, id_empresa, entrada)
    return {"filas_ok": len(resultado.filas), "filas_con_error": len(resultado.errores),
            "errores": resultado.errores[:50], "advertencias": resultado.advertencias,
            "muestra": [_vista(f) for f in resultado.filas[:8]]}


@router.post("/empresas/{id_empresa}/importaciones/{token}/confirmar")
def confirmar(token: str, entrada: MapeoEntrada, conn: Conn, id_empresa: EmpresaEditable, usuario: Usuario) -> dict:
    staging, resultado = _procesar(token, id_empresa, entrada)
    if not resultado.filas:
        raise HTTPException(422, "Ninguna fila es válida. Revisa los errores y corrige tu archivo.")
    reporte = carga.cargar(conn, id_empresa, usuario["id_usuario"], staging["tipo"], staging["nombre_archivo"], resultado)
    carga.borrar_staging(token)
    return reporte


@router.get("/empresas/{id_empresa}/importaciones")
def historial(conn: Conn, id_empresa: EmpresaId) -> list[dict]:
    return carga.historial(conn, id_empresa)


@router.delete("/empresas/{id_empresa}/importaciones/{id_importacion}")
def deshacer(id_importacion: int, conn: Conn, id_empresa: EmpresaEditable) -> dict:
    try:
        return carga.deshacer(conn, id_empresa, id_importacion)
    except LookupError as error:
        raise HTTPException(404, "No encontramos esa importación.") from error
