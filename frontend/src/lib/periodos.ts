// Periodos del filtro global (mes / trimestre / año), calculados a partir de las fechas con datos.

export type TipoPeriodo = "mes" | "trimestre" | "anio";

export interface OpcionPeriodo {
  clave: string;
  etiqueta: string;
  desde: string;
  hasta: string;
}

const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
  "Noviembre", "Diciembre"];

const iso = (a: number, m: number, d: number) => `${a}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
const finDeMes = (a: number, m: number) => new Date(a, m, 0).getDate();

export function opcionesPeriodo(tipo: TipoPeriodo, primer: string, ultimo: string): OpcionPeriodo[] {
  const [a0, m0] = primer.split("-").map(Number);
  const [a1, m1] = ultimo.split("-").map(Number);
  const opciones: OpcionPeriodo[] = [];
  if (tipo === "mes") {
    for (let a = a1, m = m1; a > a0 || (a === a0 && m >= m0); m === 1 ? ((a -= 1), (m = 12)) : (m -= 1)) {
      opciones.push({ clave: `${a}-${m}`, etiqueta: `${MESES[m - 1]} ${a}`, desde: iso(a, m, 1), hasta: iso(a, m, finDeMes(a, m)) });
    }
  } else if (tipo === "trimestre") {
    for (let a = a1, t = Math.ceil(m1 / 3); a > a0 || (a === a0 && t >= Math.ceil(m0 / 3)); t === 1 ? ((a -= 1), (t = 4)) : (t -= 1)) {
      const mi = (t - 1) * 3 + 1;
      opciones.push({ clave: `${a}-T${t}`, etiqueta: `${t}.º trimestre ${a}`, desde: iso(a, mi, 1), hasta: iso(a, mi + 2, finDeMes(a, mi + 2)) });
    }
  } else {
    for (let a = a1; a >= a0; a -= 1) {
      const hasta = a === a1 ? iso(a1, m1, finDeMes(a1, m1)) : iso(a, 12, 31);
      opciones.push({ clave: `${a}`, etiqueta: a === a1 && m1 < 12 ? `${a} (en lo que va)` : `${a}`, desde: iso(a, 1, 1), hasta });
    }
  }
  return opciones;
}

/** Últimos `meses` meses de calendario que terminan en el mes de la fecha de corte
 * (pestañas 1M, 3M, 6M, 1A, 2A). Alinear a meses completos hace que la comparación
 * con el periodo anterior sea limpia: jul–sep contra abr–jun. */
export function rangoAtras(corte: string, meses: number): { desde: string; hasta: string } {
  const [a, m] = corte.split("-").map(Number);
  const inicio = new Date(a, m - meses, 1);
  return { desde: iso(inicio.getFullYear(), inicio.getMonth() + 1, 1), hasta: corte };
}

/** Últimos 12 meses completos que terminan en el mes de `hasta` (para gráficas mensuales). */
export function ultimosMeses(hasta: string, n: number, primer: string): { desde: string; hasta: string } {
  const [a, m] = hasta.split("-").map(Number);
  const inicio = new Date(a, m - n, 1);
  const desde = iso(inicio.getFullYear(), inicio.getMonth() + 1, 1);
  return { desde: desde < primer ? primer.slice(0, 8) + "01" : desde, hasta };
}
