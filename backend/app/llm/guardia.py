"""Guardia de cifras: el LLM solo puede usar números que el código le dio.

Principio 2 de CLAUDE.md: "el código calcula, el LLM explica". Aunque el prompt lo pide,
un modelo pequeño (llama3.2:3b) a veces redondea, suma o inventa. Aquí se revisa cada
oración del texto generado: si contiene una cifra que no está en los datos permitidos,
la oración se descarta.
"""

import re

_NUMERO = re.compile(r"\d[\d,]*(?:\.\d+)?")
_ORACION = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡*\-•])")
# Números pequeños de uso común en el lenguaje ("2 productos", "1 mes", "30 días").
_LIBRES = {str(n) for n in range(0, 11)} | {"30", "100"}


def normalizar(numero: str) -> str:
    limpio = numero.replace(",", "")
    if "." in limpio:
        limpio = limpio.rstrip("0").rstrip(".")
    return limpio or "0"


def numeros(texto: str) -> set[str]:
    return {normalizar(n) for n in _NUMERO.findall(texto)}


def cifras_permitidas(*fuentes: object) -> set[str]:
    """Extrae todas las cifras de los textos/estructuras de referencia."""
    permitidas = set(_LIBRES)
    for fuente in fuentes:
        permitidas |= numeros(str(fuente))
    return permitidas


def filtrar(texto: str, permitidas: set[str]) -> tuple[str, list[str]]:
    """Devuelve el texto sin las oraciones con cifras no permitidas y la lista de cifras rechazadas."""
    conservadas, rechazadas = [], []
    for linea in texto.splitlines():
        oraciones_ok = []
        for oracion in _ORACION.split(linea):
            invalidas = numeros(oracion) - permitidas
            if invalidas:
                rechazadas.extend(sorted(invalidas))
            else:
                oraciones_ok.append(oracion)
        if oraciones_ok or not linea.strip():
            conservadas.append(" ".join(oraciones_ok))
    return "\n".join(conservadas).strip(), rechazadas
