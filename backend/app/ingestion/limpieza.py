"""Limpieza y validación fila por fila. Nunca falla en silencio: cada fila rechazada
lleva su número (como aparece en Excel) y el motivo en lenguaje simple."""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.ingestion.campos import campos_de

MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "set": 9,
         "oct": 10, "nov": 11, "dic": 12, "jan": 1, "apr": 4, "aug": 8, "dec": 12}
FORMATOS_FECHA = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
                  "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y", "%d.%m.%Y", "%Y/%m/%d", "%m/%d/%Y")
CENT = Decimal("0.01")
PALABRAS_FIJO = ("renta", "sueldo", "nomina", "salario", "luz", "cfe", "agua", "internet", "telefono", "software",
                 "seguro", "licencia", "mensualidad", "sistema")
PALABRAS_RETIRO = ("retiro", "uso personal", "personal", "dueno")
CATEGORIAS = (("renta", "Renta"), ("sueldo", "Sueldos"), ("nomina", "Sueldos"), ("salario", "Sueldos"),
              ("luz", "Servicios"), ("agua", "Servicios"), ("internet", "Servicios"), ("telefono", "Servicios"),
              ("gas", "Servicios"), ("flete", "Fletes"), ("gasolina", "Fletes"), ("envio", "Fletes"),
              ("comision", "Comisiones"), ("publicidad", "Publicidad"), ("bolsa", "Insumos"), ("limpieza", "Insumos"),
              ("mantenimiento", "Mantenimiento"), ("reparacion", "Mantenimiento"), ("retiro", "Retiros del dueño"))


def _plano(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def parse_numero(texto: str) -> Decimal | None:
    s = str(texto).strip()
    if not s:
        return None
    negativo = (s.startswith("(") and s.endswith(")")) or s.lstrip("$ ").startswith("-")
    s = re.sub(r"[^\d,.]", "", s)
    if not s or not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        valor = Decimal(s)
    except InvalidOperation:
        return None
    return -valor if negativo else valor


def parse_fecha(texto: str) -> datetime | None:
    s = str(texto).strip()
    if not s:
        return None
    if re.fullmatch(r"\d{5}(\.\d+)?", s):          # número de serie de Excel
        serie = float(s)
        if 20000 < serie < 80000:
            return datetime(1899, 12, 30) + timedelta(days=serie)
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(s, formato)
        except ValueError:
            continue
    # "15 sep 2026", "15-sep-26", "15 de septiembre de 2026"
    m = re.fullmatch(r"(\d{1,2})[\s\-/]+(?:de\s+)?([a-zA-Záéíóú]{3,})\.?[\s\-/]+(?:de(?:l)?\s+)?(\d{2,4})", s, re.IGNORECASE)
    if m:
        mes = MESES.get(_plano(m.group(2))[:3])
        anio = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
        if mes:
            try:
                return datetime(anio, mes, int(m.group(1)))
            except ValueError:
                return None
    return None


def texto_seguro(texto: str) -> tuple[str, bool]:
    """Evita inyección de fórmulas: quita = + - @ al inicio de un texto (no se ejecuta nada)."""
    limpio = texto.strip()
    peligroso = bool(limpio) and limpio[0] in "=+-@\t\r"
    while limpio and limpio[0] in "=+-@\t\r":
        limpio = limpio[1:].strip()
    return limpio[:150], peligroso


def tipo_de_gasto(valor: str, concepto: str, categoria: str) -> str:
    v = _plano(valor)
    if v.startswith("fij"):
        return "fijo"
    if v.startswith("var"):
        return "variable"
    if v.startswith("ret") or "personal" in v:
        return "retiro"
    texto = _plano(f"{concepto} {categoria}")
    if any(p in texto for p in PALABRAS_RETIRO):
        return "retiro"
    if any(p in texto for p in PALABRAS_FIJO):
        return "fijo"
    return "variable"


def categoria_de_gasto(concepto: str) -> str:
    texto = _plano(concepto)
    return next((cat for palabra, cat in CATEGORIAS if palabra in texto), "Otros")


@dataclass
class Resultado:
    filas: list[dict] = field(default_factory=list)
    errores: list[dict] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)


def limpiar(tipo: str, columnas: list[str], filas: list[list[str]], mapeo: dict[str, str | None],
            numeros: list[int], hoy: date | None = None) -> Resultado:
    hoy = hoy or date.today()
    indice = {campo: columnas.index(col) for col, campo in mapeo.items() if campo and col in columnas}
    requeridos = {c.clave: c.etiqueta for c in campos_de(tipo) if c.requerido}
    res = Resultado()
    vistos: set[tuple] = set()
    duplicados = sospechosos = 0

    for n, fila in enumerate(filas):
        numero_fila = numeros[n] if n < len(numeros) else n + 2
        valor = {campo: fila[j] if j < len(fila) else "" for campo, j in indice.items()}

        def error(motivo: str) -> None:
            res.errores.append({"fila": numero_fila, "motivo": motivo})

        faltan = [et for clave, et in requeridos.items() if not valor.get(clave, "").strip()]
        if faltan:
            error(f"Falta {', '.join(faltan)}")
            continue

        limpio: dict = {}
        if "fecha" in requeridos:
            fecha = parse_fecha(valor["fecha"])
            if fecha is None:
                error(f"No entendí la fecha \"{valor['fecha']}\" (usa día/mes/año)")
                continue
            if fecha.date() > hoy + timedelta(days=1) or fecha.year < 2000:
                error(f"La fecha {fecha:%d/%m/%Y} está fuera de rango")
                continue
            limpio["fecha"] = fecha

        problema = None
        for campo in ("cantidad", "precio_unitario", "costo_unitario", "total", "precio_venta", "costo", "stock",
                      "stock_minimo", "monto"):
            if campo in valor and valor[campo].strip():
                numero = parse_numero(valor[campo])
                if numero is None:
                    problema = f"\"{valor[campo]}\" no es un número válido"
                    break
                if numero < 0 and campo != "stock":
                    problema = f"El valor {valor[campo]} no puede ser negativo"
                    break
                limpio[campo] = numero
        if problema:
            error(problema)
            continue
        if "cantidad" in requeridos and limpio.get("cantidad", Decimal(0)) <= 0:
            error("La cantidad debe ser mayor que cero")
            continue

        for campo in ("producto", "concepto", "categoria", "proveedor", "unidad"):
            if campo in valor and valor[campo].strip():
                texto, peligroso = texto_seguro(valor[campo])
                sospechosos += peligroso
                limpio[campo] = texto
        if tipo in ("ventas", "productos", "compras") and not limpio.get("producto"):
            error("Falta el nombre del producto")
            continue

        # Precio / costo unitario a partir del total (el código hace la división, no la IA).
        if tipo == "ventas" and "precio_unitario" not in limpio:
            if "total" not in limpio:
                error("Falta el precio unitario o el total")
                continue
            limpio["precio_unitario"] = (limpio["total"] / limpio["cantidad"]).quantize(CENT, ROUND_HALF_UP)
        if tipo == "compras" and "costo_unitario" not in limpio:
            if "total" not in limpio:
                error("Falta el costo unitario o el total")
                continue
            limpio["costo_unitario"] = (limpio["total"] / limpio["cantidad"]).quantize(CENT, ROUND_HALF_UP)
        if tipo == "gastos":
            if limpio["monto"] <= 0:
                error("El monto debe ser mayor que cero")
                continue
            limpio.setdefault("categoria", categoria_de_gasto(limpio["concepto"]))
            limpio["tipo"] = tipo_de_gasto(valor.get("tipo", ""), limpio["concepto"], limpio["categoria"])

        clave = tuple(sorted((k, str(v)) for k, v in limpio.items()))
        if clave in vistos:
            duplicados += 1
            continue
        vistos.add(clave)
        limpio["_fila"] = numero_fila
        res.filas.append(limpio)

    if duplicados:
        res.advertencias.append(f"Quité {duplicados} fila(s) repetidas.")
    if sospechosos:
        res.advertencias.append(f"{sospechosos} celda(s) parecían fórmulas; las guardé como texto simple.")
    return res
