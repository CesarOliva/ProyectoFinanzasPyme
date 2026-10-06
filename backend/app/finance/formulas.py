"""Fórmulas financieras de CLAUDE.md §7.

Funciones puras (sin base de datos) para que sean fáciles de probar. Trabajan con Decimal
para que los centavos cuadren. Cuando una división no tiene sentido (ventas en cero,
margen negativo) devuelven None en lugar de inventar un número.
"""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENT, ROUND_HALF_UP)


def utilidad_bruta(ventas: Decimal, costo_ventas: Decimal) -> Decimal:
    """Lo que te queda después de pagar la mercancía que vendiste."""
    return ventas - costo_ventas


def utilidad(utilidad_bruta_: Decimal, gastos_operacion: Decimal, impuestos: Decimal = Decimal(0)) -> Decimal:
    """Lo que ganaste. En fase 1 los impuestos son 0 (no calculados)."""
    return utilidad_bruta_ - gastos_operacion - impuestos


def margen(utilidad_: Decimal, ventas: Decimal) -> Decimal | None:
    """Utilidad / ventas (fracción, p. ej. 0.382 = 38.2%)."""
    if ventas == 0:
        return None
    return utilidad_ / ventas


def margen_producto(precio: Decimal, costo: Decimal) -> Decimal | None:
    """(precio − costo) / precio."""
    if precio == 0:
        return None
    return (precio - costo) / precio


def margen_contribucion(ventas: Decimal, costos_variables: Decimal) -> Decimal | None:
    """(ventas − costos variables) / ventas."""
    if ventas == 0:
        return None
    return (ventas - costos_variables) / ventas


def punto_equilibrio(gastos_fijos: Decimal, margen_contribucion_: Decimal | None) -> Decimal | None:
    """Ventas necesarias para no perder ni ganar: gastos fijos / margen de contribución."""
    if margen_contribucion_ is None or margen_contribucion_ <= 0:
        return None
    return redondear(gastos_fijos / margen_contribucion_)


def margen_seguridad(ventas: Decimal, punto_equilibrio_: Decimal | None) -> Decimal | None:
    """Cuánto pueden bajar tus ventas antes de empezar a perder."""
    if punto_equilibrio_ is None:
        return None
    return ventas - punto_equilibrio_


def dias_inventario(stock_actual: Decimal, ventas_diarias_promedio: Decimal) -> Decimal | None:
    """Días que te alcanza el inventario al ritmo de venta actual."""
    if ventas_diarias_promedio <= 0:
        return None
    return stock_actual / ventas_diarias_promedio


def variacion(actual: Decimal, anterior: Decimal) -> Decimal | None:
    """Cambio porcentual (fracción) frente al periodo anterior."""
    if anterior == 0:
        return None
    return (actual - anterior) / abs(anterior)


def semaforo_inventario(dias: Decimal | None, umbral_rojo: float) -> str:
    """🟢 / 🟡 / 🔴 según los días de inventario."""
    if dias is None:
        return "sin_movimiento"
    if dias <= Decimal(str(umbral_rojo)):
        return "rojo"
    if dias <= Decimal(str(umbral_rojo)) * 2:
        return "amarillo"
    return "verde"
