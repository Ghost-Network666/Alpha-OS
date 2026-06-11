"use client";

import React, { useState } from "react";
import { KeyRound, Plus, Trash2, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";

interface KeyEntry {
  key: string;
  value: string;
  category?: string;
  description?: string;
}

const SUGGESTED = [
  { key: "OPENAI_API_KEY", category: "llm", description: "OpenAI / compatible" },
  { key: "ANTHROPIC_API_KEY", category: "llm", description: "Claude" },
  { key: "GROQ_API_KEY", category: "llm", description: "Groq" },
  { key: "XAI_API_KEY", category: "llm", description: "xAI / Grok" },
  { key: "ELEVENLABS_API_KEY", category: "voice", description: "TTS" },
  { key: "HERMES_API_SERVER_KEY", category: "hermes", description: "Alpha <-> Hermes auth" },
];

export function KeysView() {
  const [entries, setEntries] = useState<KeyEntry[]>([
    { key: "HERMES_API_SERVER_KEY", value: "••••••••••••", category: "hermes", description: "Internal" },
  ]);
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [reveal, setReveal] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);

  const toggleReveal = (k: string) => {
    setReveal((r) => ({ ...r, [k]: !r[k] }));
  };

  const addKey = () => {
    if (!newKey.trim()) return;
    setEntries((prev) => [
      ...prev.filter((e) => e.key !== newKey.trim()),
      { key: newKey.trim(), value: newValue || "••••••••", category: "custom" },
    ]);
    setNewKey("");
    setNewValue("");
  };

  const removeKey = (key: string) => {
    setEntries((prev) => prev.filter((e) => e.key !== key));
  };

  const saveToEnv = async () => {
    setSaving(true);
    // In real usage this would call a backend endpoint that writes ~/.hermes/.env (or routes through hermes config)
    // For now just simulate + note that user can also use Settings or hermes cli.
    await new Promise((r) => setTimeout(r, 420));
    setSaving(false);
    alert("Keys staged. For production persistence use `hermes config set` or write to ~/.hermes/.env and restart gateway.");
  };

  return (
    <div className="space-y-4 pb-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[#00f5ff]">
          <KeyRound className="h-4 w-4" />
          <span className="text-sm font-semibold tracking-[0.08em] uppercase">Keys &amp; Environment</span>
        </div>
        <Button onClick={saveToEnv} disabled={saving} variant="outline" prefix={<Plus className="h-3.5 w-3.5" />}>
          {saving ? "Saving…" : "Persist to .env"}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Current Keys
            <Badge tone="secondary">{entries.length} configured</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {entries.length === 0 && (
            <div className="py-6 text-center text-xs text-slate-500">No keys yet. Add below or via Hermes CLI.</div>
          )}
          {entries.map((e) => {
            const shown = reveal[e.key] ? e.value : (e.value.startsWith("•") ? e.value : "••••••••••••");
            return (
              <div key={e.key} className="flex items-center gap-3 rounded-lg border border-slate-800 bg-[#0a0a0f] px-3 py-2">
                <div className="min-w-0 flex-1 font-mono text-xs">
                  <div className="text-[#00f5ff]">{e.key}</div>
                  <div className="text-slate-500 text-[10px]">{e.description || e.category}</div>
                </div>
                <div className="font-mono text-xs text-slate-400 tabular-nums">{shown}</div>
                <Button variant="ghost" size="icon" onClick={() => toggleReveal(e.key)} aria-label="Toggle reveal">
                  {reveal[e.key] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </Button>
                <Button variant="ghost" size="icon" onClick={() => removeKey(e.key)} aria-label="Remove">
                  <Trash2 className="h-3.5 w-3.5 text-[#ff3366]" />
                </Button>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Add / Update Key</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              className="sm:w-72"
              placeholder="KEY_NAME"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value.toUpperCase())}
              list="suggested-keys"
            />
            <datalist id="suggested-keys">
              {SUGGESTED.map((s) => (
                <option key={s.key} value={s.key} />
              ))}
            </datalist>
            <Input
              className="flex-1 font-mono"
              placeholder="value (will be redacted on save)"
              type="password"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
            />
            <Button onClick={addKey} prefix={<Plus className="h-3.5 w-3.5" />} disabled={!newKey.trim()}>
              Add
            </Button>
          </div>
          <div className="mt-3 text-[10px] text-slate-500">
            Suggested: {SUGGESTED.map((s) => s.key).join(" • ")}
          </div>
        </CardContent>
      </Card>

      <div className="text-[10px] text-slate-500 leading-relaxed">
        Alpha OS writes some secrets via the Settings flow. For full Hermes-native keys (model providers, tools) prefer the Keys page when running inside Hermes dashboard or use <code>hermes env</code>. Changes here are staged for the current session.
      </div>
    </div>
  );
}
