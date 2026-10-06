"""Fórmulas de §7 y caso base de §12 (enero-septiembre 2026)."""

from decimal import Decimal as D

from app.finance import formulas as f


def test_caso_base_cuadra():
    ventas, costo, gastos = D("170000"), D("75000"), D("30000")
    bruta = f.utilidad_bruta(ventas, costo)
    neta = f.utilidad(bruta, gastos)
    assert bruta == D("95000")
    assert neta == D("65000")
    assert round(f.margen(neta, ventas) * 100, 1) == D("38.2")


def test_impuestos_fase_2_por_defecto_cero():
    assert f.utilidad(D("95000"), D("30000")) == f.utilidad(D("95000"), D("30000"), D("0"))


def test_margen_sin_ventas_es_none():
    assert f.margen(D("100"), D("0")) is None


def test_margen_producto():
    assert f.margen_producto(D("45"), D("24")) == D("21") / D("45")
    assert f.margen_producto(D("0"), D("10")) is None


def test_punto_equilibrio_y_margen_seguridad():
    mc = f.margen_contribucion(D("170000"), D("75000"))  # 55.88%
    pe = f.punto_equilibrio(D("18000"), mc)
    assert pe == D("32210.53")
    assert f.margen_seguridad(D("170000"), pe) == D("137789.47")


def test_punto_equilibrio_sin_margen_positivo():
    assert f.punto_equilibrio(D("1000"), D("0")) is None
    assert f.punto_equilibrio(D("1000"), D("-0.1")) is None
    assert f.punto_equilibrio(D("1000"), None) is None
    assert f.margen_seguridad(D("1000"), None) is None


def test_dias_inventario():
    assert f.dias_inventario(D("30"), D("3")) == D("10")
    assert f.dias_inventario(D("30"), D("0")) is None


def test_variacion():
    assert f.variacion(D("110"), D("100")) == D("0.1")
    assert f.variacion(D("90"), D("100")) == D("-0.1")
    assert f.variacion(D("10"), D("0")) is None


def test_semaforo_inventario():
    assert f.semaforo_inventario(D("3"), 7) == "rojo"
    assert f.semaforo_inventario(D("10"), 7) == "amarillo"
    assert f.semaforo_inventario(D("30"), 7) == "verde"
    assert f.semaforo_inventario(None, 7) == "sin_movimiento"
