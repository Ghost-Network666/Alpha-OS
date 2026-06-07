/** Alpha reply speech — server TTS stream with browser synthesis fallback. */

import { fetchTtsAudio } from "@/lib/api";

let voicesReady = false;
let activeAudio: HTMLAudioElement | null = null;

function ensureVoicesLoaded(): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  const voices = window.speechSynthesis.getVoices();
  if (voices.length > 0) {
    voicesReady = true;
    return;
  }
  if (voicesReady) return;
  window.speechSynthesis.onvoiceschanged = () => {
    if (window.speechSynthesis.getVoices().length > 0) {
      voicesReady = true;
    }
  };
}

function pickVoice(voiceHint?: string): SpeechSynthesisVoice | null {
  if (typeof window === "undefined" || !window.speechSynthesis) return null;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;

  const hint = (voiceHint ?? "").trim().toLowerCase();
  if (hint) {
    const byName = voices.find(
      (v) =>
        v.name.toLowerCase().includes(hint) ||
        hint.includes(v.name.toLowerCase())
    );
    if (byName) return byName;

    const langPrefix = hint.split("-").slice(0, 2).join("-");
    if (langPrefix) {
      const byLang = voices.find((v) =>
        v.lang.toLowerCase().startsWith(langPrefix.toLowerCase())
      );
      if (byLang) return byLang;
    }
  }

  return (
    voices.find((v) => v.lang.toLowerCase().startsWith("en")) ??
    voices[0] ??
    null
  );
}

function speakBrowser(text: string, voiceHint?: string): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  const voice = pickVoice(voiceHint);
  if (voice) utterance.voice = voice;
  utterance.rate = 1;
  utterance.pitch = 1;

  window.speechSynthesis.speak(utterance);
}

async function playAudioBlob(blob: Blob): Promise<boolean> {
  if (typeof window === "undefined") return false;

  stopAlphaSpeech();

  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  activeAudio = audio;

  return new Promise((resolve) => {
    const cleanup = () => {
      URL.revokeObjectURL(url);
      if (activeAudio === audio) activeAudio = null;
    };
    audio.onended = () => {
      cleanup();
      resolve(true);
    };
    audio.onerror = () => {
      cleanup();
      resolve(false);
    };
    void audio.play().catch(() => {
      cleanup();
      resolve(false);
    });
  });
}

export async function speakAlphaReply(
  text: string,
  voiceHint?: string,
  provider?: string
): Promise<void> {
  const trimmed = text.trim();
  if (!trimmed || typeof window === "undefined") return;

  const useServer =
    provider === "edge" ||
    provider === "grok" ||
    provider === "xai" ||
    !provider;

  if (useServer) {
    try {
      const blob = await fetchTtsAudio(trimmed, provider, voiceHint);
      if (blob) {
        const played = await playAudioBlob(blob);
        if (played) return;
      }
    } catch {
      // Fall through to browser TTS.
    }
  }

  ensureVoicesLoaded();

  if (window.speechSynthesis.getVoices().length > 0) {
    speakBrowser(trimmed, voiceHint);
    return;
  }

  const retry = () => {
    window.speechSynthesis.onvoiceschanged = null;
    speakBrowser(trimmed, voiceHint);
  };
  window.speechSynthesis.onvoiceschanged = retry;
  window.speechSynthesis.getVoices();
}

export function stopAlphaSpeech(): void {
  if (typeof window === "undefined") return;
  if (activeAudio) {
    activeAudio.pause();
    activeAudio = null;
  }
  window.speechSynthesis?.cancel();
}