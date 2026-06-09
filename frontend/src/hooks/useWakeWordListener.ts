"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { clientLog } from "@/lib/client-log";
import { micBlockedReason } from "@/lib/secure-context";
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
  tailscaleHttpsUrl?: string | null;
  onWake?: () => void;
  onCommand: (command: string) => void | Promise<void>;
  onStatus?: (status: WakeWordStatus, detail?: string) => void;
}

const DEFAULT_WAKE = "hey alpha";
const WAKE_COOLDOWN_MS = 4000;

export function useWakeWordListener({
  enabled,
  wakeWord = DEFAULT_WAKE,
  tailscaleHttpsUrl,
  onWake,
  onCommand,
  onStatus,
}: UseWakeWordListenerOptions) {
  const [status, setStatus] = useState<WakeWordStatus>("idle");
  const [detail, setDetail] = useState<string | undefined>();
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const armedRef = useRef(false);
  const wakeAnnouncedRef = useRef(false);
  const lastWakeAtRef = useRef(0);
  const lastCommandRef = useRef("");
  const onCommandRef = useRef(onCommand);
  const onWakeRef = useRef(onWake);
  const onStatusRef = useRef(onStatus);

  useEffect(() => {
    onCommandRef.current = onCommand;
    onWakeRef.current = onWake;
    onStatusRef.current = onStatus;
  }, [onCommand, onWake, onStatus]);

  const setWakeStatus = useCallback((next: WakeWordStatus, msg?: string) => {
    setStatus(next);
    setDetail(msg);
    onStatusRef.current?.(next, msg);
  }, []);

  const announceWake = useCallback(() => {
    const now = Date.now();
    if (now - lastWakeAtRef.current < WAKE_COOLDOWN_MS) return;
    lastWakeAtRef.current = now;
    onWakeRef.current?.();
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
      wakeAnnouncedRef.current = false;
      stopRecognition();
      return;
    }

    const blocked = micBlockedReason(tailscaleHttpsUrl);
    if (blocked) {
      setWakeStatus("error", "Voice needs HTTPS — use the secure link above");
      return;
    }

    const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SR) {
      setWakeStatus("unsupported", "Web Speech API unavailable in this browser");
      return;
    }

    let cancelled = false;
    setWakeStatus("loading");

    const dispatchCommand = (command: string) => {
      const cmd = command.trim();
      if (!cmd || cmd === lastCommandRef.current) return;
      lastCommandRef.current = cmd;
      armedRef.current = false;
      wakeAnnouncedRef.current = false;
      setWakeStatus("capturing");
      void Promise.resolve(onCommandRef.current(cmd)).finally(() => {
        lastCommandRef.current = "";
        setWakeStatus("listening");
      });
    };

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

        const isFinal = ev.results[ev.results.length - 1]?.isFinal;

        if (hasWakeWord(text, wakeWord)) {
          const command = stripWakeWord(text, wakeWord);
          if (command && isFinal) {
            dispatchCommand(command);
          } else if (!command) {
            if (!armedRef.current) {
              armedRef.current = true;
              if (!wakeAnnouncedRef.current) {
                wakeAnnouncedRef.current = true;
                announceWake();
              }
              setWakeStatus("capturing");
            }
          }
          return;
        }

        if (armedRef.current && isFinal && text) {
          dispatchCommand(text);
        }
      };

      rec.onerror = (ev: Event & { error?: string }) => {
        if (cancelled) return;
        const code = (ev as { error?: string }).error;
        if (code === "not-allowed") {
          const msg = "Microphone permission denied";
          clientLog("warning", msg, code, "wake");
          setWakeStatus("error", msg);
          return;
        }
        if (code !== "aborted" && code !== "no-speech") {
          const msg = code ?? "Speech recognition error";
          clientLog("warning", "Speech recognition error", msg, "wake");
          setWakeStatus("error", msg);
        }
      };

      rec.onend = () => {
        if (!cancelled) {
          armedRef.current = false;
          wakeAnnouncedRef.current = false;
          window.setTimeout(start, 300);
        }
      };

      try {
        rec.start();
        setWakeStatus("listening");
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Failed to start speech recognition";
        clientLog("error", "Failed to start speech recognition", msg, "wake");
        setWakeStatus("error", msg);
      }
    };

    start();

    return () => {
      cancelled = true;
      armedRef.current = false;
      wakeAnnouncedRef.current = false;
      stopRecognition();
    };
  }, [
    enabled,
    wakeWord,
    tailscaleHttpsUrl,
    setWakeStatus,
    stopRecognition,
    announceWake,
  ]);

  return { status, detail };
}