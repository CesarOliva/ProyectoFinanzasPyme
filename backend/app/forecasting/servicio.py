"""Pronósticos de series de tiempo.

Fase 1: línea base con promedio móvil. La interfaz `ForecastService` está pensada para
reemplazarse por Prophet / ARIMA / Holt-Winters en fase 2 sin tocar los endpoints:
basta con escribir otra clase con el mismo método `pronosticar` y cambiar `get_forecast_service`.
"""

import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class Punto:
    fecha: date
    valor: float


@dataclass(frozen=True)
class PuntoPronostico:
    fecha: date
    valor: float
    inferior: float
    superior: float


class ForecastService(Protocol):
    metodo: str

    def pronosticar(self, historico: list[Punto], horizonte_dias: int) -> list[PuntoPronostico]:
        """Recibe una serie diaria (sin huecos) y devuelve `horizonte_dias` puntos futuros."""
        ...


def completar_dias(puntos: list[tuple[date, Decimal | float]], desde: date, hasta: date) -> list[Punto]:
    """Rellena con 0 los días sin movimiento para que la serie sea diaria y continua."""
    por_dia = {f: float(v) for f, v in puntos}
    serie = []
    actual = desde
    while actual <= hasta:
        serie.append(Punto(actual, por_dia.get(actual, 0.0)))
        actual += timedelta(days=1)
    return serie


class PromedioMovil:
    """Línea base: el promedio de los últimos `ventana` días se repite hacia adelante.

    La banda (rango probable) es ±1.28 desviaciones estándar diarias, acumuladas con √k
    para un horizonte de k días cuando se pronostica un acumulado.
    """

    metodo = "promedio_movil"

    def __init__(self, ventana: int = 30):
        self.ventana = ventana

    def pronosticar(self, historico: list[Punto], horizonte_dias: int) -> list[PuntoPronostico]:
        if not historico:
            return []
        recientes = [p.valor for p in historico[-self.ventana:]]
        promedio = statistics.fmean(recientes)
        desviacion = statistics.pstdev(recientes) if len(recientes) > 1 else 0.0
        ultimo = historico[-1].fecha
        return [
            PuntoPronostico(
                fecha=ultimo + timedelta(days=k),
                valor=round(promedio, 2),
                inferior=round(max(0.0, promedio - 1.28 * desviacion), 2),
                superior=round(promedio + 1.28 * desviacion, 2),
            )
            for k in range(1, horizonte_dias + 1)
        ]

    def acumulado(self, historico: list[Punto], horizonte_dias: int) -> list[PuntoPronostico]:
        """Pronóstico del total acumulado día a día (útil para flujo de efectivo)."""
        if not historico:
            return []
        recientes = [p.valor for p in historico[-self.ventana:]]
        promedio = statistics.fmean(recientes)
        desviacion = statistics.pstdev(recientes) if len(recientes) > 1 else 0.0
        ultimo = historico[-1].fecha
        return [
            PuntoPronostico(
                fecha=ultimo + timedelta(days=k),
                valor=round(promedio * k, 2),
                inferior=round(promedio * k - 1.28 * desviacion * math.sqrt(k), 2),
                superior=round(promedio * k + 1.28 * desviacion * math.sqrt(k), 2),
            )
            for k in range(1, horizonte_dias + 1)
        ]


def get_forecast_service() -> PromedioMovil:
    return PromedioMovil(ventana=30)
