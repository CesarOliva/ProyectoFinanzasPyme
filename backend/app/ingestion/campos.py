"""Campos canónicos que se pueden importar, con sinónimos para el mapeo por reglas."""

from dataclasses import dataclass
from typing import Literal

TipoDatos = Literal["ventas", "productos", "compras", "gastos"]
TIPOS: tuple[TipoDatos, ...] = ("ventas", "productos", "compras", "gastos")


@dataclass(frozen=True)
class Campo:
    clave: str
    etiqueta: str
    requerido: bool
    descripcion: str
    ejemplo: str
    sinonimos: tuple[str, ...] = ()


_FECHA = ("fecha", "dia", "fecha de venta", "fecha venta", "fecha de compra", "fecha compra", "fecha del gasto", "date")
_PRODUCTO = ("producto", "articulo", "descripcion", "nombre", "prenda", "nombre del producto", "mercancia", "item",
             "sku", "codigo")   # en orden de prioridad
_CANTIDAD = ("cantidad", "cant", "piezas", "pzas", "unidades", "uds", "kilos", "kg", "qty", "cant vendida", "no de piezas")

CAMPOS: dict[str, list[Campo]] = {
    "ventas": [
        Campo("fecha", "Fecha", True, "Día de la venta (y hora si la tienes)", "15/09/2026", _FECHA),
        Campo("producto", "Producto", True, "Nombre o código del producto vendido", "Cuaderno profesional", _PRODUCTO),
        Campo("cantidad", "Cantidad", True, "Unidades vendidas", "3", _CANTIDAD),
        Campo("precio_unitario", "Precio unitario", False, "Precio de venta por unidad", "45.00",
              ("precio", "p unitario", "precio unitario", "precio de venta", "precio venta", "pu", "p u", "venta unitaria",
               "precio publico")),
        Campo("costo_unitario", "Costo unitario", False, "Lo que te costó cada unidad (opcional)", "24.00",
              ("costo", "costo unitario", "c unitario", "costo de compra", "costo compra", "cu")),
        Campo("total", "Total de la venta", False, "Importe total (se usa si no hay precio unitario)", "135.00",
              ("total", "importe", "monto", "subtotal", "venta", "total venta")),
        Campo("categoria", "Categoría", False, "Tipo de producto (opcional)", "Cuadernos", ("categoria", "linea", "departamento", "familia")),
    ],
    "productos": [
        Campo("producto", "Producto", True, "Nombre o código del producto", "Cuaderno profesional", _PRODUCTO),
        Campo("categoria", "Categoría", False, "Tipo de producto", "Cuadernos", ("categoria", "linea", "departamento", "familia")),
        Campo("precio_venta", "Precio de venta", True, "A cuánto lo vendes", "45.00",
              ("precio", "precio de venta", "precio venta", "precio publico", "p venta", "pvp")),
        Campo("costo", "Costo", True, "Cuánto te cuesta", "24.00",
              ("costo", "costo unitario", "costo promedio", "precio de compra", "precio compra", "p compra")),
        Campo("stock", "Existencia", False, "Cuántas unidades tienes hoy", "40",
              ("stock", "existencia", "existencias", "inventario", "en almacen", "disponible", "cantidad")),
        Campo("stock_minimo", "Mínimo", False, "Cantidad mínima antes de resurtir", "10", ("minimo", "stock minimo", "punto de reorden")),
        Campo("unidad", "Unidad", False, "pieza, kg, litro…", "pieza", ("unidad", "um", "unidad de medida", "presentacion")),
    ],
    "compras": [
        Campo("fecha", "Fecha", True, "Día de la compra", "10/09/2026", _FECHA),
        Campo("producto", "Producto", True, "Producto que compraste", "Cuaderno profesional", _PRODUCTO),
        Campo("cantidad", "Cantidad", True, "Unidades compradas", "50", _CANTIDAD),
        Campo("costo_unitario", "Costo unitario", False, "Lo que pagaste por unidad", "24.00",
              ("costo", "costo unitario", "costo c u", "precio de compra", "precio compra", "precio", "p unitario", "cu")),
        Campo("total", "Total", False, "Importe total (se usa si no hay costo unitario)", "1200.00",
              ("total", "importe", "monto", "subtotal")),
        Campo("proveedor", "Proveedor", False, "A quién le compraste", "Papelera del Centro", ("proveedor", "distribuidor", "surtidor")),
    ],
    "gastos": [
        Campo("fecha", "Fecha", True, "Día del gasto", "01/09/2026", _FECHA),
        Campo("concepto", "Concepto", True, "En qué gastaste", "Renta del local",
              ("concepto", "descripcion", "detalle", "gasto", "motivo")),
        Campo("monto", "Monto", True, "Cuánto pagaste", "1200.00", ("monto", "importe", "total", "cantidad", "pago", "cargo")),
        Campo("categoria", "Categoría", False, "Renta, Servicios, Sueldos, Insumos…", "Renta", ("categoria", "rubro", "clasificacion")),
        Campo("tipo", "Tipo", False, "fijo o variable (si no lo pones, lo deduzco)", "fijo",
              ("tipo", "tipo de gasto", "clase")),
    ],
}


def campos_de(tipo: str) -> list[Campo]:
    return CAMPOS[tipo]


def claves_de(tipo: str) -> set[str]:
    return {c.clave for c in CAMPOS[tipo]}
