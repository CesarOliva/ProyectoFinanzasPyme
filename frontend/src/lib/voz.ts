// Voz en español: reconocimiento (hablarle a Clara) y síntesis (Clara responde en voz alta).
// Usa la Web Speech API del navegador: funciona sin costo en Chrome y Edge.

import { useCallback, useEffect, useRef, useState } from "react";

interface ResultadoVoz {
  isFinal: boolean;
  0: { transcript: string };
}
interface EventoVoz {
  resultIndex: number;
  results: ArrayLike<ResultadoVoz>;
}
interface Reconocedor {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: EventoVoz) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

function crearReconocedor(): Reconocedor | null {
  const w = window as unknown as Record<string, new () => Reconocedor>;
  const Clase = w.SpeechRecognition ?? w.webkitSpeechRecognition;
  return Clase ? new Clase() : null;
}

export const vozSoportada = {
  escuchar: typeof window !== "undefined" && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window),
  hablar: typeof window !== "undefined" && "speechSynthesis" in window,
};

/** Micrófono: devuelve el texto parcial mientras hablas y llama `alTerminar` con la frase final. */
export function useReconocimiento(alTerminar: (texto: string) => void) {
  const [escuchando, setEscuchando] = useState(false);
  const [parcial, setParcial] = useState("");
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<Reconocedor | null>(null);
  const finalRef = useRef("");
  const callback = useRef(alTerminar);
  callback.current = alTerminar;

  const detener = useCallback(() => ref.current?.stop(), []);

  const iniciar = useCallback(() => {
    const rec = crearReconocedor();
    if (!rec) {
      setError("Tu navegador no permite dictar. Usa Chrome o Edge.");
      return;
    }
    window.speechSynthesis?.cancel();
    finalRef.current = "";
    setParcial("");
    setError(null);
    rec.lang = "es-MX";
    rec.continuous = false;
    rec.interimResults = true;
    rec.onresult = (e) => {
      let texto = "";
      for (let i = 0; i < e.results.length; i += 1) texto += e.results[i][0].transcript;
      setParcial(texto);
      if (e.results[e.results.length - 1]?.isFinal) finalRef.current = texto;
    };
    rec.onerror = (e) => {
      if (e.error === "not-allowed") setError("Permite el uso del micrófono para hablarle a Clara.");
      else if (e.error !== "no-speech" && e.error !== "aborted") setError("No te escuché bien. Intenta otra vez.");
    };
    rec.onend = () => {
      setEscuchando(false);
      const texto = finalRef.current.trim();
      if (texto) callback.current(texto);
      setParcial("");
    };
    ref.current = rec;
    rec.start();
    setEscuchando(true);
  }, []);

  useEffect(() => () => ref.current?.abort(), []);
  return { escuchando, parcial, error, iniciar, detener };
}

function vozEspanol(): SpeechSynthesisVoice | undefined {
  const voces = window.speechSynthesis.getVoices();
  return (
    voces.find((v) => v.lang === "es-MX" && /natural|online/i.test(v.name)) ??
    voces.find((v) => v.lang === "es-MX") ??
    voces.find((v) => v.lang === "es-US") ??
    voces.find((v) => v.lang.startsWith("es"))
  );
}

/** Lectura en voz alta. Divide en frases para que los textos largos no se corten en Chrome. */
export function useSintesis() {
  const [hablando, setHablando] = useState<string | null>(null);

  useEffect(() => {
    if (!vozSoportada.hablar) return;
    window.speechSynthesis.getVoices();
    const cargar = () => window.speechSynthesis.getVoices();
    window.speechSynthesis.addEventListener?.("voiceschanged", cargar);
    return () => {
      window.speechSynthesis.removeEventListener?.("voiceschanged", cargar);
      window.speechSynthesis.cancel();
    };
  }, []);

  const callar = useCallback(() => {
    window.speechSynthesis?.cancel();
    setHablando(null);
  }, []);

  const hablar = useCallback((texto: string, id = "voz") => {
    if (!vozSoportada.hablar || !texto) return;
    const sintesis = window.speechSynthesis;
    sintesis.cancel();
    const voz = vozEspanol();
    const frases = texto.match(/[^.!?]+[.!?]*/g) ?? [texto];
    frases.forEach((frase, i) => {
      const u = new SpeechSynthesisUtterance(frase.trim());
      u.lang = voz?.lang ?? "es-MX";
      if (voz) u.voice = voz;
      u.rate = 1.03;
      u.pitch = 1;
      if (i === 0) u.onstart = () => setHablando(id);
      if (i === frases.length - 1) u.onend = () => setHablando(null);
      u.onerror = () => setHablando(null);
      sintesis.speak(u);
    });
  }, []);

  return { hablando, hablar, callar };
}
