import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

type Params = Record<string, string | number | boolean | null | undefined>;

/** GET con estados de carga y error. Se vuelve a pedir cuando cambian la ruta o los parámetros. */
export function useApi<T>(ruta: string | null, params?: Params) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(Boolean(ruta));
  const clave = ruta ? `${ruta}?${JSON.stringify(params ?? {})}` : null;
  const paramsRef = useRef(params);
  paramsRef.current = params;
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!clave || !ruta) return;
    const control = new AbortController();
    setCargando(true);
    setError(null);
    api
      .get<T>(ruta, paramsRef.current, control.signal)
      .then((d) => setDatos(d))
      .catch((e: Error) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!control.signal.aborted) setCargando(false);
      });
    return () => control.abort();
  }, [clave, ruta, version]);

  const recargar = useCallback(() => setVersion((v) => v + 1), []);
  return { datos, error, cargando, recargar, setDatos };
}
