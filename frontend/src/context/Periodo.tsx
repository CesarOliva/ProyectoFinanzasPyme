import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { opcionesPeriodo, type OpcionPeriodo, type TipoPeriodo } from "../lib/periodos";
import { useSesion } from "./Sesion";

interface ValorPeriodo {
  tipo: TipoPeriodo;
  setTipo: (t: TipoPeriodo) => void;
  opciones: OpcionPeriodo[];
  seleccion: OpcionPeriodo | null;
  setClave: (clave: string) => void;
  /** Parámetros listos para la API. */
  params: { desde?: string; hasta?: string };
}

const Contexto = createContext<ValorPeriodo | null>(null);

export function ProveedorPeriodo({ children }: { children: ReactNode }) {
  const { empresa } = useSesion();
  const [tipo, setTipo] = useState<TipoPeriodo>("mes");
  const [clave, setClave] = useState<string | null>(null);

  const opciones = useMemo(
    () => (empresa?.primer_dato && empresa.ultimo_dato ? opcionesPeriodo(tipo, empresa.primer_dato, empresa.ultimo_dato) : []),
    [tipo, empresa?.primer_dato, empresa?.ultimo_dato],
  );

  // Al cambiar de empresa o de tipo, se elige el periodo más reciente.
  useEffect(() => setClave(opciones[0]?.clave ?? null), [opciones]);

  const seleccion = opciones.find((o) => o.clave === clave) ?? opciones[0] ?? null;
  const valor = useMemo<ValorPeriodo>(
    () => ({
      tipo,
      setTipo,
      opciones,
      seleccion,
      setClave,
      params: seleccion ? { desde: seleccion.desde, hasta: seleccion.hasta } : {},
    }),
    [tipo, opciones, seleccion],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function usePeriodo() {
  const v = useContext(Contexto);
  if (!v) throw new Error("usePeriodo fuera de ProveedorPeriodo");
  return v;
}
