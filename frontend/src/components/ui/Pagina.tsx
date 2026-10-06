import { motion } from "framer-motion";
import type { ReactNode } from "react";

/** Contenedor de cada módulo: encabezado consistente y transición de entrada. */
export function Pagina({
  eyebrow,
  titulo,
  descripcion,
  acciones,
  children,
}: {
  eyebrow?: string;
  titulo: string;
  descripcion?: string;
  acciones?: ReactNode;
  children: ReactNode;
}) {
  return (
    <motion.main
      className="pagina"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      <header className="encabezado-pagina">
        <div className="titulo">
          {eyebrow && <span className="eyebrow">{eyebrow}</span>}
          <h1>{titulo}</h1>
          {descripcion && <p className="justificado">{descripcion}</p>}
        </div>
        {acciones && <div className="fila envolver">{acciones}</div>}
      </header>
      {children}
    </motion.main>
  );
}
