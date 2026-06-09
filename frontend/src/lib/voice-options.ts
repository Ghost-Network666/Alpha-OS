export const MODEL_PROVIDERS = [
  { id: "xai-oauth", label: "xAI / Grok (OAuth)" },
  { id: "openai", label: "OpenAI" },
  { id: "anthropic", label: "Anthropic" },
  { id: "openrouter", label: "OpenRouter" },
  { id: "nous", label: "Nous Research" },
  { id: "groq", label: "Groq" },
  { id: "auto", label: "Auto-detect" },
] as const;

export const XAI_VOICES = [
  { id: "eve", label: "Eve" },
  { id: "ara", label: "Ara" },
  { id: "rex", label: "Rex" },
  { id: "sal", label: "Sal" },
  { id: "leo", label: "Leo" },
] as const;

export const EDGE_VOICES = [
  { id: "en-US-AriaNeural", label: "Aria (US)" },
  { id: "en-US-GuyNeural", label: "Guy (US)" },
  { id: "en-US-JennyNeural", label: "Jenny (US)" },
  { id: "en-GB-SoniaNeural", label: "Sonia (UK)" },
  { id: "en-GB-RyanNeural", label: "Ryan (UK)" },
] as const;

export const ELEVENLABS_MODELS = [
  { id: "eleven_multilingual_v2", label: "Multilingual v2" },
  { id: "eleven_turbo_v2_5", label: "Turbo v2.5" },
  { id: "eleven_flash_v2_5", label: "Flash v2.5" },
] as const;

export const STT_MODELS: Record<string, string[]> = {
  local: ["tiny", "base", "small", "medium", "large"],
  xai: ["base"],
  groq: ["whisper-large-v3", "whisper-large-v3-turbo"],
  openai: ["whisper-1"],
  mistral: ["voxtral-mini-latest"],
  elevenlabs: ["scribe_v2"],
};