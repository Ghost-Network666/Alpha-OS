/** Strip the wake phrase and return the command portion, if any. */
export function stripWakeWord(transcript: string, wakeWord: string): string {
  const text = transcript.trim();
  if (!text) return "";

  const normalized = text.toLowerCase();
  const wake = wakeWord.toLowerCase().trim();
  const variants = [wake, "hey alfa", "hey alba"];

  for (const phrase of variants) {
    const idx = normalized.indexOf(phrase);
    if (idx !== -1) {
      return text.slice(idx + phrase.length).trim();
    }
  }

  return text;
}

export function hasWakeWord(transcript: string, wakeWord: string): boolean {
  const normalized = transcript.toLowerCase();
  const wake = wakeWord.toLowerCase().trim();
  return (
    normalized.includes(wake) ||
    normalized.includes("hey alfa") ||
    normalized.includes("hey alba")
  );
}