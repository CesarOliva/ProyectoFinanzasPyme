import { describe, expect, it } from "vitest";
import { textoALeer, textoInterrumpido } from "../context/Chat";
import { cambio, dinero, pct, textoParaVoz } from "../lib/formato";
import { opcionesPeriodo, rangoAtras, ultimosMeses } from "../lib/periodos";
import type { ChatRespuesta } from "../lib/tipos";

describe("formato", () => {
  it("formatea pesos mexicanos", () => {
    expect(dinero(170000)).toBe("$170,000");
    expect(dinero(1234.5)).toBe("$1,234.50");
    expect(dinero(null)).toBe("—");
  });
  it("formatea porcentajes y cambios", () => {
    expect(pct(0.3824)).toBe("38.2%");
    expect(cambio(0.123)).toBe("+12.3%");
    expect(cambio(-0.583)).toBe("−58.3%");
    expect(cambio(-60.9)).toBe("−más de 999%");
    expect(cambio(null)).toBe("sin comparación");
  });
  it("prepara texto para la voz", () => {
    const texto = textoParaVoz("### Título\n- **Vendiste:** $17,650\n- Margen: 38.2%\n🔴 Alerta");
    expect(texto).toContain("17,650 pesos");
    expect(texto).toContain("38 punto 2 por ciento");
    expect(texto).not.toMatch(/[#*🔴]/u);
  });
});

describe("periodos", () => {
  it("lista meses del más reciente al más antiguo", () => {
    const meses = opcionesPeriodo("mes", "2024-10-01", "2026-09-30");
    expect(meses).toHaveLength(24);
    expect(meses[0]).toMatchObject({ desde: "2026-09-01", hasta: "2026-09-30", etiqueta: "Septiembre 2026" });
    expect(meses[23].desde).toBe("2024-10-01");
  });
  it("el año en curso termina en el último mes con datos", () => {
    const anios = opcionesPeriodo("anio", "2024-10-01", "2026-09-30");
    expect(anios[0]).toMatchObject({ desde: "2026-01-01", hasta: "2026-09-30", etiqueta: "2026 (en lo que va)" });
    expect(anios.map((a) => a.clave)).toEqual(["2026", "2025", "2024"]);
  });
  it("trimestres", () => {
    const t = opcionesPeriodo("trimestre", "2024-10-01", "2026-09-30");
    expect(t[0]).toMatchObject({ desde: "2026-07-01", hasta: "2026-09-30" });
    expect(t).toHaveLength(8);
  });
  it("rangos de la gráfica principal", () => {
    expect(rangoAtras("2026-09-30", 1)).toEqual({ desde: "2026-09-01", hasta: "2026-09-30" });
    expect(rangoAtras("2026-09-30", 3)).toEqual({ desde: "2026-07-01", hasta: "2026-09-30" });
    expect(rangoAtras("2026-09-30", 24)).toEqual({ desde: "2024-10-01", hasta: "2026-09-30" });
    expect(ultimosMeses("2026-09-30", 12, "2024-10-01")).toEqual({ desde: "2025-10-01", hasta: "2026-09-30" });
    expect(ultimosMeses("2024-11-30", 12, "2024-10-01").desde).toBe("2024-10-01");
  });
});

describe("lectura en voz alta", () => {
  const base: Omit<ChatRespuesta, "answer"> = {
    intencion: "analisis_completo",
    periodo: { desde: "2026-01-01", hasta: "2026-09-30", etiqueta: "enero a septiembre 2026" },
    fuente: "ollama",
    sugerencias: [],
    datos: {},
  };
  it("en respuestas largas lee solo título, interpretación y primera recomendación", () => {
    const answer = `### Análisis financiero\n\n**Ingresos**\n${"- Línea con cifras $1,000\n".repeat(40)}\n**Lo que significa**\n\nVas bien este año.\n\n**Recomendaciones**\n- Revisa tus precios.\n- Otra cosa.`;
    const texto = textoALeer({ ...base, answer });
    expect(texto).toContain("Vas bien este año");
    expect(texto).toContain("Revisa tus precios");
    expect(texto).not.toContain("Línea con cifras");
    expect(texto).not.toContain("Otra cosa");
  });
});

describe("interrupción del chat", () => {
  it("si aún no había nada, queda solo '...'", () => {
    expect(textoInterrumpido({ id: "1", rol: "clara", texto: "", estado: "pensando" })).toBe("...");
  });
  it("conserva las cifras y lo que alcanzó a escribir la IA, terminando en '...'", () => {
    const t = textoInterrumpido({ id: "1", rol: "clara", texto: "", estado: "escribiendo", base: "### Ventas", narrativa: "Vas bien este " });
    expect(t).toBe("### Ventas\n\n**Lo que significa**\n\nVas bien este...");
  });
  it("con cifras pero sin texto de la IA, termina en '...'", () => {
    expect(textoInterrumpido({ id: "1", rol: "clara", texto: "", estado: "escribiendo", base: "### Ventas" })).toBe("### Ventas\n\n...");
  });
});
