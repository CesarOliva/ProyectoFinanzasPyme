"""Utilidades de periodos (mes, trimestre, año) y periodo de comparación."""

import calendar
from datetime import date, timedelta

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def fin_de_mes(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def sumar_meses(d: date, n: int) -> date:
    indice = d.year * 12 + d.month - 1 + n
    anio, mes = divmod(indice, 12)
    return date(anio, mes + 1, min(d.day, calendar.monthrange(anio, mes + 1)[1]))


def es_mes_completo(desde: date, hasta: date) -> bool:
    return desde.day == 1 and hasta == fin_de_mes(hasta)


def numero_meses(desde: date, hasta: date) -> int:
    return (hasta.year - desde.year) * 12 + hasta.month - desde.month + 1


def periodo_anterior(desde: date, hasta: date) -> tuple[date, date]:
    """Periodo inmediato anterior de la misma duración (meses completos si aplica)."""
    if es_mes_completo(desde, hasta):
        n = numero_meses(desde, hasta)
        inicio = sumar_meses(desde, -n)
        return inicio, fin_de_mes(sumar_meses(desde, -1))
    duracion = (hasta - desde).days + 1
    return desde - timedelta(days=duracion), desde - timedelta(days=1)


def meses_en(desde: date, hasta: date) -> list[tuple[int, int]]:
    meses = []
    actual = desde.replace(day=1)
    while actual <= hasta:
        meses.append((actual.year, actual.month))
        actual = sumar_meses(actual, 1)
    return meses


def etiqueta_mes(anio: int, mes: int) -> str:
    return f"{MESES_CORTOS[mes - 1]} {str(anio)[2:]}"


def describir_periodo(desde: date, hasta: date) -> str:
    """Texto legible: 'septiembre 2026', 'enero a septiembre 2026', '1 al 15 de marzo 2026'."""
    if es_mes_completo(desde, hasta):
        if (desde.year, desde.month) == (hasta.year, hasta.month):
            return f"{MESES[desde.month - 1]} {desde.year}"
        if desde.year == hasta.year:
            return f"{MESES[desde.month - 1]} a {MESES[hasta.month - 1]} {hasta.year}"
        return f"{MESES[desde.month - 1]} {desde.year} a {MESES[hasta.month - 1]} {hasta.year}"
    return f"{desde:%d/%m/%Y} al {hasta:%d/%m/%Y}"
