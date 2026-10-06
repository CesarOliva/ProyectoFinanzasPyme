"""Staging, carga a las tablas finales (en una transacción) y deshacer.

Decisión: las existencias (stock) se toman del catálogo de productos. Importar ventas o
compras históricas NO modifica el stock, porque el catálogo ya refleja el inventario de hoy
y restar ventas pasadas lo contaría dos veces.
"""

import json
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from sqlalchemy import Connection, func, insert, select, update

from app.config import get_settings
from app.db import models as m
from app.ingestion.lectura import TablaLeida
from app.ingestion.limpieza import Resultado

HORAS_STAGING = 24


class StagingNoEncontrado(LookupError):
    pass


def _carpeta() -> Path:
    carpeta = Path(get_settings().carpeta_staging)
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def guardar_staging(tabla: TablaLeida, id_empresa: int, id_usuario: int, tipo: str, nombre_archivo: str) -> str:
    carpeta = _carpeta()
    limite = time.time() - HORAS_STAGING * 3600
    for viejo in carpeta.glob("*.json"):
        if viejo.stat().st_mtime < limite:
            viejo.unlink(missing_ok=True)
    token = uuid.uuid4().hex
    datos = {"id_empresa": id_empresa, "id_usuario": id_usuario, "tipo": tipo, "nombre_archivo": nombre_archivo,
             "tabla": asdict(tabla)}
    (carpeta / f"{token}.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return token


def leer_staging(token: str, id_empresa: int) -> dict:
    if not token.isalnum():
        raise StagingNoEncontrado(token)
    ruta = _carpeta() / f"{token}.json"
    if not ruta.exists():
        raise StagingNoEncontrado(token)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if datos["id_empresa"] != id_empresa:            # el token no es de esta empresa
        raise StagingNoEncontrado(token)
    datos["tabla"] = TablaLeida(**datos["tabla"])
    return datos


def borrar_staging(token: str) -> None:
    (_carpeta() / f"{token}.json").unlink(missing_ok=True)


def _productos_por_nombre(conn: Connection, id_empresa: int) -> dict[str, dict]:
    filas = conn.execute(select(m.productos_cat).where(m.productos_cat.c.id_empresa == id_empresa)).mappings()
    return {f["sku_o_nombre"].strip().lower(): dict(f) for f in filas}


def _asegurar_producto(conn: Connection, id_empresa: int, id_importacion: int, catalogo: dict[str, dict], fila: dict,
                       creados: list[str]) -> int:
    clave = fila["producto"].strip().lower()
    if clave in catalogo:
        return catalogo[clave]["id_producto"]
    nuevo = {
        "id_empresa": id_empresa, "sku_o_nombre": fila["producto"], "categoria": fila.get("categoria") or "General",
        "unidad": "pieza", "stock_actual": 0, "stock_minimo": 0,
        "costo_promedio": fila.get("costo_unitario") or 0, "precio_venta": fila.get("precio_unitario") or 0,
        "id_importacion": id_importacion,
    }
    id_producto = conn.execute(insert(m.productos_cat).values(**nuevo)).inserted_primary_key[0]
    catalogo[clave] = {**nuevo, "id_producto": id_producto}
    creados.append(fila["producto"])
    return id_producto


def cargar(conn: Connection, id_empresa: int, id_usuario: int, tipo: str, nombre_archivo: str,
           limpio: Resultado) -> dict:
    """Inserta todo dentro de la transacción de `conn`; si algo falla, la transacción hace rollback."""
    estado = "con_errores" if limpio.errores else "completada"
    id_importacion = conn.execute(insert(m.importaciones).values(
        id_empresa=id_empresa, id_usuario=id_usuario, nombre_archivo=nombre_archivo[:255], tipo_datos=tipo,
        fecha=datetime.now(), estado=estado, filas_ok=0, filas_con_error=len(limpio.errores),
        detalle_errores={"errores": limpio.errores[:500], "advertencias": limpio.advertencias},
    )).inserted_primary_key[0]

    catalogo = _productos_por_nombre(conn, id_empresa)
    creados: list[str] = []
    actualizados = 0
    registros: list[dict] = []

    for fila in limpio.filas:
        if tipo == "ventas":
            id_producto = _asegurar_producto(conn, id_empresa, id_importacion, catalogo, fila, creados)
            costo = fila.get("costo_unitario")
            if costo is None:
                costo = catalogo[fila["producto"].strip().lower()]["costo_promedio"] or 0
            registros.append({"id_empresa": id_empresa, "id_producto": id_producto, "fecha_hora": fila["fecha"],
                              "cantidad_vendida": fila["cantidad"], "precio_unitario": fila["precio_unitario"],
                              "costo_unitario": costo, "id_importacion": id_importacion})
        elif tipo == "compras":
            id_producto = _asegurar_producto(conn, id_empresa, id_importacion, catalogo, fila, creados)
            registros.append({"id_empresa": id_empresa, "id_producto": id_producto, "fecha": fila["fecha"].date(),
                              "cantidad": fila["cantidad"], "costo_unitario": fila["costo_unitario"],
                              "proveedor": fila.get("proveedor"), "id_importacion": id_importacion})
        elif tipo == "gastos":
            registros.append({"id_empresa": id_empresa, "fecha": fila["fecha"].date(), "concepto": fila["concepto"],
                              "categoria": fila["categoria"][:80], "tipo": fila["tipo"], "monto": fila["monto"],
                              "id_importacion": id_importacion})
        elif tipo == "productos":
            clave = fila["producto"].strip().lower()
            datos = {"categoria": fila.get("categoria"), "precio_venta": fila.get("precio_venta"),
                     "costo_promedio": fila.get("costo"), "stock_actual": fila.get("stock"),
                     "stock_minimo": fila.get("stock_minimo"), "unidad": fila.get("unidad")}
            datos = {k: v for k, v in datos.items() if v is not None}
            if clave in catalogo:
                conn.execute(update(m.productos_cat)
                             .where(m.productos_cat.c.id_producto == catalogo[clave]["id_producto"],
                                    m.productos_cat.c.id_empresa == id_empresa)
                             .values(**datos))
                actualizados += 1
            else:
                nuevo = {"id_empresa": id_empresa, "sku_o_nombre": fila["producto"], "id_importacion": id_importacion,
                         "categoria": "General", "unidad": "pieza", **datos}
                id_producto = conn.execute(insert(m.productos_cat).values(**nuevo)).inserted_primary_key[0]
                catalogo[clave] = {**nuevo, "id_producto": id_producto}
                creados.append(fila["producto"])

    tabla = {"ventas": m.historial_ventas, "compras": m.compras_producto, "gastos": m.gastos_operativos}.get(tipo)
    if tabla is not None and registros:
        conn.execute(insert(tabla), registros)

    filas_ok = len(limpio.filas)
    conn.execute(update(m.importaciones).where(m.importaciones.c.id_importacion == id_importacion)
                 .values(filas_ok=filas_ok))
    return {"id_importacion": id_importacion, "estado": estado, "filas_ok": filas_ok,
            "filas_con_error": len(limpio.errores), "errores": limpio.errores[:200],
            "advertencias": limpio.advertencias, "productos_creados": creados, "productos_actualizados": actualizados}


def deshacer(conn: Connection, id_empresa: int, id_importacion: int) -> dict:
    imp = conn.execute(select(m.importaciones).where(m.importaciones.c.id_importacion == id_importacion,
                                                     m.importaciones.c.id_empresa == id_empresa)).mappings().first()
    if imp is None:
        raise LookupError(id_importacion)
    if imp["estado"] == "deshecha":
        return {"id_importacion": id_importacion, "borradas": 0, "productos_borrados": 0}
    borradas = 0
    for tabla in (m.historial_ventas, m.compras_producto, m.gastos_operativos):
        borradas += conn.execute(tabla.delete().where(tabla.c.id_empresa == id_empresa,
                                                      tabla.c.id_importacion == id_importacion)).rowcount
    # Productos creados por esta importación que ya no tienen movimientos.
    creados = conn.execute(select(m.productos_cat.c.id_producto).where(
        m.productos_cat.c.id_empresa == id_empresa, m.productos_cat.c.id_importacion == id_importacion)).scalars().all()
    productos_borrados = 0
    for id_producto in creados:
        usos = conn.execute(select(func.count()).select_from(m.historial_ventas)
                            .where(m.historial_ventas.c.id_producto == id_producto)).scalar() + \
            conn.execute(select(func.count()).select_from(m.compras_producto)
                         .where(m.compras_producto.c.id_producto == id_producto)).scalar()
        if not usos:
            conn.execute(m.productos_cat.delete().where(m.productos_cat.c.id_producto == id_producto))
            productos_borrados += 1
    conn.execute(update(m.importaciones).where(m.importaciones.c.id_importacion == id_importacion)
                 .values(estado="deshecha"))
    return {"id_importacion": id_importacion, "borradas": borradas, "productos_borrados": productos_borrados}


def historial(conn: Connection, id_empresa: int) -> list[dict]:
    filas = conn.execute(select(m.importaciones).where(m.importaciones.c.id_empresa == id_empresa)
                         .order_by(m.importaciones.c.fecha.desc()).limit(50)).mappings()
    resultado = []
    for f in filas:
        detalle = f["detalle_errores"]
        if isinstance(detalle, str):
            detalle = json.loads(detalle or "null")
        resultado.append({"id_importacion": f["id_importacion"], "nombre_archivo": f["nombre_archivo"],
                          "tipo_datos": f["tipo_datos"], "fecha": f["fecha"], "estado": f["estado"],
                          "filas_ok": f["filas_ok"], "filas_con_error": f["filas_con_error"],
                          "errores": (detalle or {}).get("errores", [])[:20]})
    return resultado
