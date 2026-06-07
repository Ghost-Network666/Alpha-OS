/** Browser TTS for Alpha replies via window.speechSynthesis. */

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

export function speakAlphaReply(text: string, voiceHint?: string): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  const trimmed = text.trim();
  if (!trimmed) return;

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(trimmed);
  const voice = pickVoice(voiceHint);
  if (voice) utterance.voice = voice;
  utterance.rate = 1;
  utterance.pitch = 1;

  window.speechSynthesis.speak(utterance);
}

export function stopAlphaSpeech(): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
}