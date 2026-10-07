"""Pipeline de ingesta con 5 formatos realistas (tests/fixtures)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.ingestion.lectura import ArchivoInvalido, leer_archivo
from app.ingestion.limpieza import parse_fecha, parse_numero, texto_seguro
from app.ingestion.mapeo import faltantes, por_reglas

FIXTURES = Path(__file__).parent / "fixtures"
HOY = date(2026, 10, 6)


def _leer(nombre: str):
    return leer_archivo(nombre, (FIXTURES / nombre).read_bytes(), 5)


@pytest.mark.parametrize("texto, esperado", [
    ("$1,250.00", Decimal("1250.00")), ("30,50", Decimal("30.50")), ("1.234,56", Decimal("1234.56")),
    ("1,500", Decimal("1500")), ("(50)", Decimal("-50")), ("85.5", Decimal("85.5")), ("N/A", None), ("", None),
])
def test_parse_numero(texto, esperado):
    assert parse_numero(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("15/09/2026", date(2026, 9, 15)), ("2026-09-15", date(2026, 9, 15)), ("15/09/26", date(2026, 9, 15)),
    ("15 sep 2026", date(2026, 9, 15)), ("15 de septiembre de 2026", date(2026, 9, 15)), ("46280", date(2026, 9, 15)),
])
def test_parse_fecha(texto, esperado):
    assert parse_fecha(texto).date() == esperado


def test_fecha_imposible():
    assert parse_fecha("31/02/2026") is None


def test_texto_seguro_quita_formulas():
    limpio, peligroso = texto_seguro('=HYPERLINK("http://x","clic")')
    assert peligroso and not limpio.startswith("=")


def test_rechaza_extension_y_contenido_falso():
    with pytest.raises(ArchivoInvalido):
        leer_archivo("virus.exe", b"MZ...", 5)
    with pytest.raises(ArchivoInvalido):
        leer_archivo("falso.xlsx", b"no soy un zip", 5)
    with pytest.raises(ArchivoInvalido):
        leer_archivo("grande.csv", b"a" * (2 * 1024 * 1024), 1)


def test_papeleria_titulos_y_totales():
    t = _leer("papeleria_ventas.xlsx")
    assert t.fila_encabezado == 4
    assert len(t.filas) == 5                       # sin título ni fila TOTAL
    m = por_reglas("ventas", t.columnas)
    assert m == {"Fecha": "fecha", "Artículo": "producto", "Cant.": "cantidad", "P. Unitario": "precio_unitario",
                 "Importe": "total"}


def test_abarrotes_csv_punto_y_coma_y_coma_decimal():
    t = _leer("abarrotes_ventas.csv")
    m = por_reglas("ventas", t.columnas)
    assert m["PRECIO VENTA"] == "precio_unitario" and m["PIEZAS"] == "cantidad"


def test_catalogo_prefiere_descripcion_sobre_codigo():
    m = por_reglas("productos", _leer("catalogo_productos.xlsx").columnas)
    assert m["Descripción"] == "producto" and m["Código"] is None


def test_faltantes():
    assert faltantes("ventas", {"Fecha": "fecha"}) == ["Producto", "Cantidad", "Precio unitario o Total"]
    assert faltantes("ventas", {"a": "fecha", "b": "producto", "c": "cantidad", "d": "total"}) == []


# --- Flujo completo por la API: analizar → previsualizar → confirmar → deshacer ----------------------

def _subir(cliente, headers, nombre, tipo, id_empresa=1):
    with open(FIXTURES / nombre, "rb") as f:
        r = cliente.post(f"/api/empresas/{id_empresa}/importaciones/analizar", headers=headers,
                         files={"archivo": (nombre, f)}, data={"tipo_datos": tipo})
    assert r.status_code == 200, r.text
    return r.json()


def test_flujo_completo_ventas(cliente, ana):
    analisis = _subir(cliente, ana, "papeleria_ventas.xlsx", "ventas")
    assert analisis["uso_ia"] is False                  # LLM falso apagado: solo reglas
    mapeo = {m["columna"]: m["campo"] for m in analisis["mapeo"]}
    token = analisis["token"]

    vista = cliente.post(f"/api/empresas/1/importaciones/{token}/previsualizar", headers=ana, json={"mapeo": mapeo}).json()
    assert vista["filas_ok"] == 4 and vista["filas_con_error"] == 1
    assert vista["errores"][0]["fila"] == 9

    reporte = cliente.post(f"/api/empresas/1/importaciones/{token}/confirmar", headers=ana, json={"mapeo": mapeo}).json()
    assert reporte["filas_ok"] == 4 and reporte["estado"] == "con_errores"
    assert "Producto nuevo de prueba" in reporte["productos_creados"]

    historial = cliente.get("/api/empresas/1/importaciones", headers=ana).json()
    assert historial[0]["id_importacion"] == reporte["id_importacion"]

    deshecho = cliente.delete(f"/api/empresas/1/importaciones/{reporte['id_importacion']}", headers=ana).json()
    assert deshecho["borradas"] == 4 and deshecho["productos_borrados"] == 1
    # el caso base sigue cuadrando después de deshacer
    k = cliente.get("/api/empresas/1/resumen", headers=ana, params={"desde": "2026-01-01", "hasta": "2026-09-30"}).json()["kpis"]
    assert k["ventas"] == 170000.00


def test_compras_total_a_unitario_y_duplicados(cliente, ana):
    analisis = _subir(cliente, ana, "boutique_compras.xlsx", "compras")
    mapeo = {m["columna"]: m["campo"] for m in analisis["mapeo"]}
    vista = cliente.post(f"/api/empresas/1/importaciones/{analisis['token']}/previsualizar", headers=ana,
                         json={"mapeo": mapeo}).json()
    assert vista["filas_ok"] == 2
    assert vista["muestra"][0]["costo_unitario"] == "560.00"
    assert any("repetidas" in a for a in vista["advertencias"])


def test_gastos_infiere_tipo_y_bloquea_formula(cliente, ana):
    analisis = _subir(cliente, ana, "gastos_tienda.csv", "gastos")
    mapeo = {m["columna"]: m["campo"] for m in analisis["mapeo"]}
    vista = cliente.post(f"/api/empresas/1/importaciones/{analisis['token']}/previsualizar", headers=ana,
                         json={"mapeo": mapeo}).json()
    tipos = {f["concepto"]: f["tipo"] for f in vista["muestra"]}
    assert tipos["Renta del local"] == "fijo" and tipos["Retiro personal"] == "variable"
    assert tipos["Bolsas y empaque"] == "variable"
    assert not any(c.startswith("=") for c in tipos)


def test_token_de_otra_empresa(cliente, ana, lupita):
    analisis = _subir(cliente, ana, "gastos_tienda.csv", "gastos")
    mapeo = {m["columna"]: m["campo"] for m in analisis["mapeo"]}
    r = cliente.post(f"/api/empresas/2/importaciones/{analisis['token']}/confirmar", headers=lupita, json={"mapeo": mapeo})
    assert r.status_code == 404


def test_mapeo_incompleto(cliente, ana):
    analisis = _subir(cliente, ana, "papeleria_ventas.xlsx", "ventas")
    r = cliente.post(f"/api/empresas/1/importaciones/{analisis['token']}/confirmar", headers=ana,
                     json={"mapeo": {"Fecha": "fecha"}})
    assert r.status_code == 422


def test_plantilla_descargable(cliente):
    r = cliente.get("/api/importar/plantillas/ventas")
    assert r.status_code == 200 and r.content.startswith(b"PK")
