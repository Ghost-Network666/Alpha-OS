"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { hasWakeWord, stripWakeWord } from "@/lib/wakeword";

export type WakeWordStatus =
  | "idle"
  | "loading"
  | "listening"
  | "capturing"
  | "error"
  | "unsupported";

interface UseWakeWordListenerOptions {
  enabled: boolean;
  wakeWord?: string;
  onWake?: () => void;
  onCommand: (command: string) => void | Promise<void>;
  onStatus?: (status: WakeWordStatus, detail?: string) => void;
}

const DEFAULT_WAKE = "hey alpha";

export function useWakeWordListener({
  enabled,
  wakeWord = DEFAULT_WAKE,
  onWake,
  onCommand,
  onStatus,
}: UseWakeWordListenerOptions) {
  const [status, setStatus] = useState<WakeWordStatus>("idle");
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const armedRef = useRef(false);
  const onCommandRef = useRef(onCommand);
  const onWakeRef = useRef(onWake);
  const onStatusRef = useRef(onStatus);

  useEffect(() => {
    onCommandRef.current = onCommand;
    onWakeRef.current = onWake;
    onStatusRef.current = onStatus;
  }, [onCommand, onWake, onStatus]);

  const setWakeStatus = useCallback((next: WakeWordStatus, detail?: string) => {
    setStatus(next);
    onStatusRef.current?.(next, detail);
  }, []);

  const stopRecognition = useCallback(() => {
    const rec = recognitionRef.current;
    if (!rec) return;
    try {
      rec.onresult = null;
      rec.onerror = null;
      rec.onend = null;
      rec.abort();
    } catch {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }
    recognitionRef.current = null;
  }, []);

  useEffect(() => {
    if (!enabled) {
      setWakeStatus("idle");
      armedRef.current = false;
      stopRecognition();
      return;
    }

    const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SR) {
      setWakeStatus("unsupported", "Web Speech API unavailable in this browser");
      return;
    }

    let cancelled = false;
    setWakeStatus("loading");

    const start = () => {
      if (cancelled) return;
      const rec = new SR();
      recognitionRef.current = rec;
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";

      rec.onresult = (ev: SpeechRecognitionEvent) => {
        let combined = "";
        for (let i = 0; i < ev.results.length; i++) {
          combined += ev.results[i]?.[0]?.transcript ?? "";
        }
        const text = combined.trim();
        if (!text) return;

        if (hasWakeWord(text, wakeWord)) {
          const command = stripWakeWord(text, wakeWord);
          const isFinal = ev.results[ev.results.length - 1]?.isFinal;
          onWakeRef.current?.();
          if (command && isFinal) {
            armedRef.current = false;
            setWakeStatus("capturing");
            void Promise.resolve(onCommandRef.current(command)).finally(() =>
              setWakeStatus("listening")
            );
          } else if (!command) {
            armedRef.current = true;
            setWakeStatus("capturing");
          }
          return;
        }

        if (armedRef.current) {
          const isFinal = ev.results[ev.results.length - 1]?.isFinal;
          if (isFinal && text) {
            armedRef.current = false;
            setWakeStatus("capturing");
            void Promise.resolve(onCommandRef.current(text)).finally(() =>
              setWakeStatus("listening")
            );
          }
        }
      };

      rec.onerror = (ev: Event & { error?: string }) => {
        if (cancelled) return;
        const code = (ev as { error?: string }).error;
        if (code === "not-allowed") {
          setWakeStatus("error", "Microphone permission denied");
          return;
        }
        if (code !== "aborted" && code !== "no-speech") {
          setWakeStatus("error", code ?? "Speech recognition error");
        }
      };

      rec.onend = () => {
        if (!cancelled) {
          armedRef.current = false;
          window.setTimeout(start, 300);
        }
      };

      try {
        rec.start();
        setWakeStatus("listening");
      } catch (err) {
        setWakeStatus(
          "error",
          err instanceof Error ? err.message : "Failed to start speech recognition"
        );
      }
    };

    start();

    return () => {
      cancelled = true;
      armedRef.current = false;
      stopRecognition();
    };
  }, [enabled, wakeWord, setWakeStatus, stopRecognition]);

  return { status };
}