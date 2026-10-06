import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, guardarToken, leerToken, onSesionExpirada } from "../lib/api";
import type { EmpresaResumen, InfoEmpresa, Sesion, Usuario } from "../lib/tipos";

interface ValorSesion {
  usuario: Usuario | null;
  empresas: EmpresaResumen[];
  empresa: InfoEmpresa | null;
  cargando: boolean;
  entrar: (sesion: Sesion) => void;
  salir: () => void;
  cambiarEmpresa: (id: number) => void;
  recargarEmpresa: () => Promise<void>;
}

const Contexto = createContext<ValorSesion | null>(null);
const CLAVE_EMPRESA = "cc.empresa";

function empresaGuardada(): number | null {
  try {
    const v = localStorage.getItem(CLAVE_EMPRESA);
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [empresas, setEmpresas] = useState<EmpresaResumen[]>([]);
  const [idEmpresa, setIdEmpresa] = useState<number | null>(null);
  const [empresa, setEmpresa] = useState<InfoEmpresa | null>(null);
  const [cargando, setCargando] = useState(Boolean(leerToken()));

  const salir = useCallback(() => {
    guardarToken(null);
    setUsuario(null);
    setEmpresas([]);
    setIdEmpresa(null);
    setEmpresa(null);
  }, []);

  useEffect(() => onSesionExpirada(salir), [salir]);

  const elegirEmpresa = useCallback((lista: EmpresaResumen[]) => {
    const guardada = empresaGuardada();
    const id = lista.find((e) => e.id_empresa === guardada)?.id_empresa ?? lista[0]?.id_empresa ?? null;
    setIdEmpresa(id);
  }, []);

  // Restaurar sesión al abrir la página.
  useEffect(() => {
    if (!leerToken()) return;
    api
      .get<{ usuario: Usuario; empresas: EmpresaResumen[] }>("/auth/yo")
      .then((r) => {
        setUsuario(r.usuario);
        setEmpresas(r.empresas);
        elegirEmpresa(r.empresas);
      })
      .catch(salir)
      .finally(() => setCargando(false));
  }, [elegirEmpresa, salir]);

  const recargarEmpresa = useCallback(async () => {
    if (idEmpresa === null) return;
    setEmpresa(await api.get<InfoEmpresa>(`/empresas/${idEmpresa}`));
  }, [idEmpresa]);

  useEffect(() => {
    if (idEmpresa === null) return;
    try {
      localStorage.setItem(CLAVE_EMPRESA, String(idEmpresa));
    } catch {
      /* sin almacenamiento */
    }
    setEmpresa(null);
    recargarEmpresa().catch(() => setEmpresa(null));
  }, [idEmpresa, recargarEmpresa]);

  const entrar = useCallback(
    (sesion: Sesion) => {
      guardarToken(sesion.token);
      setUsuario(sesion.usuario);
      setEmpresas(sesion.empresas);
      elegirEmpresa(sesion.empresas);
      setCargando(false);
    },
    [elegirEmpresa],
  );

  const valor = useMemo(
    () => ({ usuario, empresas, empresa, cargando, entrar, salir, cambiarEmpresa: setIdEmpresa, recargarEmpresa }),
    [usuario, empresas, empresa, cargando, entrar, salir, recargarEmpresa],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSesion() {
  const v = useContext(Contexto);
  if (!v) throw new Error("useSesion fuera de ProveedorSesion");
  return v;
}
