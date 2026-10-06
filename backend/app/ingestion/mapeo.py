"""Mapeo de columnas del archivo a campos canónicos.

1. Reglas: sinónimos conocidos ("P. Unitario" → precio_unitario).
2. IA: el LLM recibe SOLO los encabezados y 5 filas de muestra (nunca el archivo completo)
   y devuelve JSON estricto. Se valida que cada propuesta sea un campo real.
3. El usuario confirma o corrige antes de cargar nada.
"""

import json

from app.ingestion.campos import campos_de, claves_de
from app.ingestion.lectura import TablaLeida, normalizar_encabezado
from app.llm.ollama import get_llm

MUESTRA_FILAS = 5


def por_reglas(tipo: str, columnas: list[str]) -> dict[str, str | None]:
    """Cada campo toma la columna que coincide con su sinónimo de mayor prioridad
    (p. ej. "Descripción" gana a "Código" como nombre del producto)."""
    normal = {c: normalizar_encabezado(c) for c in columnas}
    resultado: dict[str, str | None] = {c: None for c in columnas}
    for exacta in (True, False):          # primero coincidencias exactas, luego parciales
        for campo in campos_de(tipo):
            if campo.clave in resultado.values():
                continue
            sinonimos = [normalizar_encabezado(s) for s in campo.sinonimos] + [campo.clave.replace("_", " ")]
            elegida = None
            for sinonimo in sinonimos:
                for columna in columnas:
                    if resultado[columna]:
                        continue
                    n = normal[columna]
                    if n == sinonimo if exacta else (sinonimo in n.split() or n.startswith(sinonimo + " ")
                                                     or n.endswith(" " + sinonimo)):
                        elegida = columna
                        break
                if elegida:
                    break
            if elegida:
                resultado[elegida] = campo.clave
    return resultado


def por_ia(tipo: str, tabla: TablaLeida) -> dict[str, str | None] | None:
    campos = campos_de(tipo)
    descripcion = "\n".join(f"- {c.clave}: {c.descripcion} (ej. {c.ejemplo})" for c in campos)
    muestra = [dict(zip(tabla.columnas, fila)) for fila in tabla.filas[:MUESTRA_FILAS]]
    sistema = (
        "Eres un asistente que mapea columnas de hojas de cálculo de tiendas mexicanas a campos de una base de datos.\n"
        f"Campos disponibles para '{tipo}':\n{descripcion}\n"
        "Reglas: cada campo se usa como máximo una vez; si una columna no corresponde a ningún campo usa null.\n"
        'Responde SOLO JSON: {"mapeo": {"<columna original>": "<campo o null>"}}'
    )
    usuario = json.dumps({"columnas": tabla.columnas, "filas_de_muestra": muestra}, ensure_ascii=False)
    crudo = get_llm().chat(sistema, usuario, formato_json=True, temperatura=0, max_tokens=300)
    if not crudo:
        return None
    try:
        propuesta = json.loads(crudo).get("mapeo", {})
    except (json.JSONDecodeError, AttributeError):
        return None
    validos = claves_de(tipo)
    resultado: dict[str, str | None] = {}
    usados: set[str] = set()
    for columna in tabla.columnas:
        campo = propuesta.get(columna)
        if isinstance(campo, str) and campo in validos and campo not in usados:
            resultado[columna] = campo
            usados.add(campo)
        else:
            resultado[columna] = None
    return resultado


def proponer(tipo: str, tabla: TablaLeida, usar_ia: bool = True) -> tuple[list[dict], bool]:
    """Combina reglas e IA. Las reglas exactas ganan; la IA completa lo que las reglas no resolvieron."""
    reglas = por_reglas(tipo, tabla.columnas)
    ia = por_ia(tipo, tabla) if usar_ia else None
    usados = {c for c in reglas.values() if c}
    mapeo = []
    for columna in tabla.columnas:
        campo, fuente = reglas[columna], "reglas" if reglas[columna] else None
        if campo is None and ia and ia.get(columna) and ia[columna] not in usados:
            campo, fuente = ia[columna], "ia"
            usados.add(campo)
        mapeo.append({"columna": columna, "campo": campo, "fuente": fuente})
    return mapeo, ia is not None


def faltantes(tipo: str, mapeo: dict[str, str | None]) -> list[str]:
    asignados = {c for c in mapeo.values() if c}
    faltan = [c.etiqueta for c in campos_de(tipo) if c.requerido and c.clave not in asignados]
    # Sin precio unitario se puede calcular con el total (y lo mismo con el costo en compras).
    if tipo == "ventas" and "precio_unitario" not in asignados and "total" not in asignados:
        faltan.append("Precio unitario o Total")
    if tipo == "compras" and "costo_unitario" not in asignados and "total" not in asignados:
        faltan.append("Costo unitario o Total")
    return faltan
