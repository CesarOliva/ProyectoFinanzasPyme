"""Formato de cifras para texto (alertas, chatbot). Las cifras se formatean en código,
nunca las escribe el LLM por su cuenta."""


def dinero(valor: float | None) -> str:
    if valor is None:
        return "sin dato"
    signo = "-" if valor < 0 else ""
    texto = f"{abs(valor):,.2f}"
    if texto.endswith(".00"):
        texto = texto[:-3]
    return f"{signo}${texto}"


def pct(valor: float | None, decimales: int = 1) -> str:
    if valor is None:
        return "sin dato"
    return f"{valor * 100:.{decimales}f}%"


def pct_cambio(valor: float | None) -> str:
    """'+12.0%' / '-8.5%'."""
    if valor is None:
        return "sin dato"
    return f"{'+' if valor >= 0 else '-'}{abs(valor) * 100:.1f}%"


def numero(valor: float | None) -> str:
    if valor is None:
        return "sin dato"
    return f"{valor:,.0f}" if float(valor).is_integer() else f"{valor:,.1f}"


def unidades(cantidad: float | None, unidad: str) -> str:
    """'3 piezas', '1 pieza', '2.5 kg', '40 hojas'."""
    if cantidad is None:
        return "sin dato"
    plural = unidad if cantidad == 1 or unidad[-1:] not in "aeiou" else unidad + "s"
    return f"{numero(cantidad)} {plural}"
