import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import { textoParaVoz } from "../lib/formato";
import type { ChatRespuesta } from "../lib/tipos";
import { useSintesis } from "../lib/voz";
import { usePeriodo } from "./Periodo";
import { useSesion } from "./Sesion";

export interface Mensaje {
  id: string;
  rol: "usuario" | "clara";
  texto: string;
  base?: string;
  narrativa?: string;
  estado: "pensando" | "escribiendo" | "listo" | "error" | "interrumpido";
  respuesta?: ChatRespuesta;
}

interface ValorChat {
  mensajes: Mensaje[];
  ocupado: boolean;
  chatAbierto: boolean;
  abrirChat: () => void;
  cerrarChat: () => void;
  alternarChat: () => void;
  enviar: (texto: string) => void;
  cancelar: () => void;
  limpiar: () => void;
  vozAutomatica: boolean;
  setVozAutomatica: (v: boolean) => void;
  hablando: string | null;
  leer: (m: Mensaje) => void;
  callar: () => void;
}

const Contexto = createContext<ValorChat | null>(null);
let contador = 0;
const nuevoId = () => `m${Date.now()}-${(contador += 1)}`;

/** Texto que queda cuando el usuario interrumpe: lo que alcanzó a escribirse y "..." al final. */
export function textoInterrumpido(m: Mensaje): string {
  if (!m.base) return "...";
  const narrativa = m.narrativa?.trim();
  return narrativa ? `${m.base}\n\n**Lo que significa**\n\n${narrativa}...` : `${m.base}\n\n...`;
}

/** Qué se lee en voz alta: respuestas cortas completas; en las largas, el título y la interpretación. */
export function textoALeer(r: ChatRespuesta): string {
  if (r.answer.length < 650) return textoParaVoz(r.answer);
  const titulo = r.answer.match(/^###\s*(.+)$/m)?.[1] ?? "";
  const significado = r.answer.match(/\*\*Lo que significa\*\*\n+([\s\S]+?)(\n\n|$)/)?.[1] ?? "";
  const recomendacion = r.answer.match(/\*\*Recomendaciones\*\*\n- (.+)/)?.[1] ?? "";
  return textoParaVoz([titulo, significado, recomendacion && `Te recomiendo: ${recomendacion}`].filter(Boolean).join(". "));
}

export function ProveedorChat({ children }: { children: ReactNode }) {
  const { empresa } = useSesion();
  const { params } = usePeriodo();
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const [chatAbierto, setChatAbierto] = useState(false);
  const [vozAutomatica, setVozAutomatica] = useState(true);
  const abrirChat = useCallback(() => setChatAbierto(true), []);
  const cerrarChat = useCallback(() => setChatAbierto(false), []);
  const alternarChat = useCallback(() => setChatAbierto((abierto) => !abierto), []);
  const control = useRef<AbortController | null>(null);
  const enCurso = useRef<string | null>(null);
  const ultimaIntencion = useRef<string | null>(null);
  const { hablando, hablar, callar } = useSintesis();

  // Cada negocio tiene su propia conversación.
  useEffect(() => {
    control.current?.abort();
    enCurso.current = null;
    setMensajes([]);
    ultimaIntencion.current = null;
  }, [empresa?.id_empresa]);

  const actualizar = useCallback((id: string, cambios: Partial<Mensaje>) => {
    setMensajes((ms) => ms.map((m) => (m.id === id ? { ...m, ...cambios } : m)));
  }, []);

  /** Detiene la respuesta en curso sin borrarla: se conserva lo escrito y termina en "...". */
  const interrumpir = useCallback(() => {
    control.current?.abort();
    control.current = null;
    const id = enCurso.current;
    enCurso.current = null;
    if (!id) return;
    setMensajes((ms) =>
      ms.map((m) =>
        m.id === id && (m.estado === "pensando" || m.estado === "escribiendo")
          ? { ...m, texto: textoInterrumpido(m), estado: "interrumpido", narrativa: undefined }
          : m,
      ),
    );
  }, []);

  const enviar = useCallback(
    (texto: string) => {
      const limpio = texto.trim();
      if (!limpio || !empresa) return;
      interrumpir();
      callar();
      const ctrl = new AbortController();
      control.current = ctrl;
      const idClara = nuevoId();
      enCurso.current = idClara;
      setMensajes((ms) => [
        ...ms,
        { id: nuevoId(), rol: "usuario", texto: limpio, estado: "listo" },
        { id: idClara, rol: "clara", texto: "", estado: "pensando" },
      ]);
      setOcupado(true);
      let narrativa = "";
      api
        .stream(
          `/empresas/${empresa.id_empresa}/chat/stream`,
          { mensaje: limpio, ...params, intencion_anterior: ultimaIntencion.current },
          (evento) => {
            if (evento.tipo === "inicio") {
              actualizar(idClara, { base: String(evento.base), estado: "escribiendo" });
            } else if (evento.tipo === "token") {
              narrativa += String(evento.texto);
              actualizar(idClara, { narrativa });
            } else if (evento.tipo === "final") {
              const r = evento.respuesta as ChatRespuesta;
              ultimaIntencion.current = r.intencion;
              if (enCurso.current === idClara) enCurso.current = null;
              actualizar(idClara, { texto: r.answer, estado: "listo", respuesta: r, narrativa: undefined });
              if (vozAutomatica) hablar(textoALeer(r), idClara);
            }
          },
          ctrl.signal,
        )
        .catch((e: Error) => {
          if (e.name === "AbortError") return;
          if (enCurso.current === idClara) enCurso.current = null;
          actualizar(idClara, { texto: e.message, estado: "error" });
        })
        .finally(() => {
          if (control.current === ctrl) setOcupado(false);
        });
    },
    [empresa, params, actualizar, callar, hablar, vozAutomatica, interrumpir],
  );

  const cancelar = useCallback(() => {
    interrumpir();
    setOcupado(false);
  }, [interrumpir]);

  const valor = useMemo<ValorChat>(
    () => ({
      mensajes,
      ocupado,
      chatAbierto,
      abrirChat,
      cerrarChat,
      alternarChat,
      enviar,
      cancelar,
      limpiar: () => setMensajes([]),
      vozAutomatica,
      setVozAutomatica: (v) => {
        if (!v) callar();
        setVozAutomatica(v);
      },
      hablando,
      leer: (m) => m.respuesta && hablar(textoALeer(m.respuesta), m.id),
      callar,
    }),
    [mensajes, ocupado, chatAbierto, abrirChat, cerrarChat, alternarChat, enviar, cancelar, vozAutomatica, hablando, hablar, callar],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useChat() {
  const v = useContext(Contexto);
  if (!v) throw new Error("useChat fuera de ProveedorChat");
  return v;
}
