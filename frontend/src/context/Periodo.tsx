import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { rangosPeriodo, ventanasPeriodo, type OpcionPeriodo, type VentanaPeriodo } from "../lib/periodos";
import { useSesion } from "./Sesion";

interface ValorPeriodo {
  /** Las anchuras del primer select: 1 mes, 2 meses, 3 meses, 6 meses, 1 año, 2 años. */
  periodos: OpcionPeriodo[];
  meses: string;
  setMeses: (meses: string) => void;
  /** Las ventanas disponibles (mes o rango de meses) para la anchura elegida. */
  ventanas: VentanaPeriodo[];
  seleccion: VentanaPeriodo | null;
  setClave: (clave: string) => void;
  /** Parámetros listos para la API. */
  params: { desde?: string; hasta?: string };
}

const Contexto = createContext<ValorPeriodo | null>(null);
const MESES_INICIAL = "3";

export function ProveedorPeriodo({ children }: { children: ReactNode }) {
  const { empresa } = useSesion();
  const [meses, setMesesEstado] = useState<string>(MESES_INICIAL);
  const [clave, setClave] = useState<string | null>(null);

  const periodos = useMemo(
    () => (empresa?.ultimo_dato ? rangosPeriodo(empresa.ultimo_dato) : []),
    [empresa?.ultimo_dato],
  );

  const ventanas = useMemo(
    () =>
      empresa?.primer_dato && empresa.ultimo_dato
        ? ventanasPeriodo(empresa.primer_dato, empresa.ultimo_dato, Number(meses))
        : [],
    [empresa?.primer_dato, empresa?.ultimo_dato, meses],
  );

  const seleccion = ventanas.find((v) => v.clave === clave) ?? ventanas[0] ?? null;

  const setMeses = (m: string) => {
    setClave(null);
    setMesesEstado(m);
  };

  const valor = useMemo<ValorPeriodo>(
    () => ({
      periodos,
      meses,
      setMeses,
      ventanas,
      seleccion,
      setClave,
      params: seleccion ? { desde: seleccion.desde, hasta: seleccion.hasta } : {},
    }),
    [periodos, meses, ventanas, seleccion],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function usePeriodo() {
  const v = useContext(Contexto);
  if (!v) throw new Error("usePeriodo fuera de ProveedorPeriodo");
  return v;
}