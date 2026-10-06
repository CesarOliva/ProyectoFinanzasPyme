import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer, Tooltip } from "recharts";
import { Ayuda, Cambio, NumeroAnimado } from "./basicos";

export interface PuntoSpark {
  etiqueta: string;
  valor: number;
}

interface Props {
  etiqueta: string;
  tecnico?: string;
  valor: number | null;
  formato: (n: number) => string;
  variacion?: number | null;
  /** Cambio en puntos porcentuales (para márgenes), en lugar de % relativo. */
  puntos?: number | null;
  invertido?: boolean;
  /** Texto bajo el cambio, p. ej. "vs $42,335 en agosto 2026". */
  comparacion?: string;
  serie?: PuntoSpark[];
  color?: string;
  indice?: number;
  nota?: string;
}

function ChipPuntos({ valor }: { valor: number | null }) {
  if (valor === null) return <span className="cambio neutro">sin comparación</span>;
  const Icono = valor > 0 ? ArrowUpRight : valor < 0 ? ArrowDownRight : Minus;
  const clase = Math.abs(valor) < 0.0005 ? "neutro" : valor > 0 ? "sube" : "baja";
  return (
    <span className={`cambio ${clase} num`}>
      <Icono size={13} aria-hidden="true" />
      {valor > 0 ? "+" : valor < 0 ? "−" : ""}
      {Math.abs(valor * 100).toFixed(1)} pts
    </span>
  );
}

function TooltipSpark({ active, payload, formato }: { active?: boolean; payload?: { payload: PuntoSpark }[]; formato: (n: number) => string }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="tooltip-spark">
      <span className="muted">{p.etiqueta}</span>
      <strong className="num">{formato(p.valor)}</strong>
    </div>
  );
}

/** Tarjeta KPI centrada: etiqueta sencilla, término técnico en tooltip, cifra animada,
 * cambio contra el periodo anterior y mini tendencia que muestra el dato al tocarla. */
export function KpiCard({
  etiqueta, tecnico, valor, formato, variacion, puntos, invertido, comparacion, serie, color = "var(--s1)", indice = 0, nota,
}: Props) {
  const id = `spark-${etiqueta.replace(/\W/g, "")}`;
  return (
    <motion.article
      className="card kpi interactiva"
      initial={{ opacity: 0, y: 18, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.5, delay: indice * 0.06, ease: [0.22, 1, 0.36, 1] }}
    >
      <span className="etiqueta">
        {etiqueta}
        {tecnico && <Ayuda texto={tecnico} />}
      </span>
      <strong className="valor">{valor === null ? "—" : <NumeroAnimado valor={valor} formato={formato} />}</strong>
      {variacion !== undefined && <Cambio valor={variacion} invertido={invertido} />}
      {puntos !== undefined && <ChipPuntos valor={puntos} />}
      {comparacion && <span className="mini muted num">{comparacion}</span>}
      {nota && <span className="mini muted">{nota}</span>}
      {serie && serie.length > 1 && (
        <div className="spark" aria-label={`Tendencia de ${etiqueta.toLowerCase()}: toca la gráfica para ver cada dato`}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={serie} margin={{ top: 4, right: 2, bottom: 2, left: 2 }}>
              <defs>
                <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Tooltip
                content={<TooltipSpark formato={formato} />}
                cursor={{ stroke: "var(--axis)", strokeWidth: 1 }}
                allowEscapeViewBox={{ x: true, y: true }}
                wrapperStyle={{ zIndex: 20, pointerEvents: "none" }}
                offset={12}
              />
              <Area type="monotone" dataKey="valor" stroke={color} strokeWidth={2} fill={`url(#${id})`} animationDuration={900}
                activeDot={{ r: 4, stroke: "var(--surface)", strokeWidth: 2, fill: color }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </motion.article>
  );
}
