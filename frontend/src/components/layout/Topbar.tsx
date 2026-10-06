import { CalendarRange, LogOut, Menu, Moon, Sun } from "lucide-react";
import { usePeriodo } from "../../context/Periodo";
import { useSesion } from "../../context/Sesion";
import type { TipoPeriodo } from "../../lib/periodos";
import { Segmentado } from "../ui/basicos";

export function Topbar({ tema, alternarTema, abrirMenu }: { tema: "light" | "dark"; alternarTema: () => void; abrirMenu: () => void }) {
  const { empresas, empresa, cambiarEmpresa, salir } = useSesion();
  const { tipo, setTipo, opciones, seleccion, setClave } = usePeriodo();
  const actual = empresas.find((e) => e.id_empresa === empresa?.id_empresa);

  return (
    <header className="topbar">
      <button className="btn icono fantasma menu-movil" onClick={abrirMenu} aria-label="Abrir menú">
        <Menu size={20} />
      </button>
      <div className="selector-empresa">
        <span className="avatar" aria-hidden="true">
          {(actual?.nombre_negocio ?? "?").charAt(0)}
        </span>
        <label className="sr-only" htmlFor="empresa">
          Negocio
        </label>
        <select id="empresa" value={empresa?.id_empresa ?? ""} onChange={(e) => cambiarEmpresa(Number(e.target.value))}>
          {empresas.map((e) => (
            <option key={e.id_empresa} value={e.id_empresa}>
              {e.nombre_negocio}
            </option>
          ))}
        </select>
        {actual?.rol === "consulta" && <span className="chip">solo lectura</span>}
      </div>
      <div className="espacio" />
      {opciones.length > 0 && (
        <div className="filtro-periodo">
          <CalendarRange size={18} color="var(--muted)" aria-hidden="true" />
          <Segmentado<TipoPeriodo>
            etiqueta="Tipo de periodo"
            valor={tipo}
            onChange={setTipo}
            opciones={[
              { valor: "mes", texto: "Mes" },
              { valor: "trimestre", texto: "Trimestre" },
              { valor: "anio", texto: "Año" },
            ]}
          />
          <label className="sr-only" htmlFor="periodo">
            Periodo
          </label>
          <select id="periodo" className="select" value={seleccion?.clave ?? ""} onChange={(e) => setClave(e.target.value)}>
            {opciones.map((o) => (
              <option key={o.clave} value={o.clave}>
                {o.etiqueta}
              </option>
            ))}
          </select>
        </div>
      )}
      <button className="btn icono fantasma" onClick={alternarTema} aria-label={tema === "dark" ? "Usar tema claro" : "Usar tema oscuro"}>
        {tema === "dark" ? <Sun size={18} /> : <Moon size={18} />}
      </button>
      <button className="btn icono fantasma" onClick={salir} aria-label="Cerrar sesión" title="Cerrar sesión">
        <LogOut size={18} />
      </button>
    </header>
  );
}
