"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchHermesProfiles,
  fetchSkillMarkdown,
  saveProfileAgent,
  type HermesProfileSummary,
} from "@/lib/api";
import { MODEL_PROVIDERS } from "@/lib/voice-options";
import { Toggle } from "@/components/Toggle";

interface AgentsSettingsTabProps {
  activeProfile: string;
  onProfileChange: (name: string) => void;
  onError: (msg: string | null) => void;
  onNote: (msg: string | null) => void;
}

export function AgentsSettingsTab({
  activeProfile,
  onProfileChange,
  onError,
  onNote,
}: AgentsSettingsTabProps) {
  const [profiles, setProfiles] = useState<HermesProfileSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [skillContent, setSkillContent] = useState<string | null>(null);
  const [modelProvider, setModelProvider] = useState("");
  const [modelDefault, setModelDefault] = useState("");
  const [toolsets, setToolsets] = useState<{ id: string; enabled: boolean }[]>(
    []
  );
  const [mcpServers, setMcpServers] = useState<
    { id: string; enabled: boolean }[]
  >([]);
  const [skills, setSkills] = useState<
    { id: string; name: string; rel_path: string }[]
  >([]);

  const applyProfile = useCallback((p: HermesProfileSummary) => {
    setModelProvider(p.model?.provider ?? "");
    setModelDefault(p.model?.default ?? "");
    setToolsets(p.toolsets ?? []);
    setMcpServers(p.mcp_servers ?? []);
    setSkills(p.skills ?? []);
    setSelectedSkill(null);
    setSkillContent(null);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const res = await fetchHermesProfiles();
      const list = res.profiles ?? [];
      setProfiles(list);
      const current =
        list.find((p) => p.name === activeProfile) ?? list[0] ?? null;
      if (current) applyProfile(current);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }, [activeProfile, applyProfile, onError]);

  useEffect(() => {
    void load();
  }, [load]);

  const selectProfile = (name: string) => {
    onProfileChange(name);
    const p = profiles.find((x) => x.name === name);
    if (p) applyProfile(p);
  };

  const toggleToolset = (id: string, enabled: boolean) => {
    setToolsets((prev) =>
      prev.map((t) => (t.id === id ? { ...t, enabled } : t))
    );
  };

  const toggleMcp = (id: string, enabled: boolean) => {
    setMcpServers((prev) =>
      prev.map((m) => (m.id === id ? { ...m, enabled } : m))
    );
  };

  const viewSkill = async (relPath: string) => {
    setSelectedSkill(relPath);
    setSkillContent(null);
    try {
      const res = await fetchSkillMarkdown(activeProfile, relPath);
      setSkillContent(res.content ?? null);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to load skill");
    }
  };

  const saveAgent = async () => {
    setSaving(true);
    onError(null);
    onNote(null);
    try {
      const disabled = toolsets.filter((t) => !t.enabled).map((t) => t.id);
      const mcp_enabled: Record<string, boolean> = {};
      for (const m of mcpServers) mcp_enabled[m.id] = m.enabled;
      const res = await saveProfileAgent(activeProfile, {
        model_provider: modelProvider.trim() || undefined,
        model_default: modelDefault.trim() || undefined,
        disabled_toolsets: disabled,
        mcp_enabled,
      });
      if (res.profile) applyProfile(res.profile);
      onNote(`Agent config saved for profile “${activeProfile}”`);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Agent save failed");
    } finally {
      setSaving(false);
    }
  };

  const current = profiles.find((p) => p.name === activeProfile);

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
          Agent profiles
        </div>
        <p className="mb-2 text-[10px] leading-relaxed text-slate-600">
          Model, toolsets, MCP, and skills per Hermes profile. Saves to{" "}
          <code className="break-all text-cyan-700">
            {current?.config_path ?? "~/.hermes/profiles/…/config.yaml"}
          </code>
        </p>
        <div className="flex flex-wrap gap-2">
          {profiles.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => selectProfile(p.name)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition ${
                p.name === activeProfile
                  ? "border-cyan-600/60 bg-cyan-950/40 text-cyan-300"
                  : "border-slate-800 text-slate-500 hover:border-slate-600"
              }`}
            >
              {p.name}
              {p.active ? " · active" : ""}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-[10px] text-slate-600">Loading agents…</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-[10px] text-slate-500">
                Model provider
              </label>
              <select
                value={modelProvider}
                onChange={(e) => setModelProvider(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
              >
                <option value="">—</option>
                {MODEL_PROVIDERS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
                {modelProvider &&
                  !MODEL_PROVIDERS.some((p) => p.id === modelProvider) && (
                    <option value={modelProvider}>{modelProvider}</option>
                  )}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] text-slate-500">
                Default model
              </label>
              <input
                value={modelDefault}
                onChange={(e) => setModelDefault(e.target.value)}
                placeholder="grok-4.3"
                className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
              />
            </div>
          </div>

          {toolsets.length > 0 && (
            <div>
              <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
                Toolsets
              </div>
              <div className="space-y-1.5">
                {toolsets.map((t) => (
                  <Toggle
                    key={t.id}
                    checked={t.enabled}
                    onChange={(on) => toggleToolset(t.id, on)}
                    label={t.id}
                  />
                ))}
              </div>
            </div>
          )}

          {mcpServers.length > 0 && (
            <div>
              <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
                MCP servers
              </div>
              <div className="space-y-1.5">
                {mcpServers.map((m) => (
                  <Toggle
                    key={m.id}
                    checked={m.enabled}
                    onChange={(on) => toggleMcp(m.id, on)}
                    label={m.id}
                    hint={m.enabled ? "Enabled" : "Disabled in profile config"}
                  />
                ))}
              </div>
            </div>
          )}

          {skills.length > 0 && (
            <div>
              <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
                Skills
              </div>
              <div className="max-h-28 space-y-1 overflow-y-auto">
                {skills.map((s) => (
                  <button
                    key={s.rel_path}
                    type="button"
                    onClick={() => void viewSkill(s.rel_path)}
                    className={`block w-full rounded border px-2 py-1 text-left text-[10px] font-mono ${
                      selectedSkill === s.rel_path
                        ? "border-cyan-700 bg-cyan-950/30 text-cyan-300"
                        : "border-slate-800 text-slate-500 hover:border-slate-600"
                    }`}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
              {skillContent && (
                <pre className="mt-2 max-h-40 overflow-auto rounded-lg border border-slate-800 bg-[#0a0a0f] p-2 text-[9px] leading-relaxed text-slate-400">
                  {skillContent.slice(0, 4000)}
                  {skillContent.length > 4000 ? "\n…" : ""}
                </pre>
              )}
            </div>
          )}

          <button
            type="button"
            onClick={() => void saveAgent()}
            disabled={saving}
            className="w-full rounded-lg border border-cyan-800/60 bg-cyan-950/30 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/30 disabled:opacity-50"
          >
            {saving ? "Saving agent…" : `Save agent config (${activeProfile})`}
          </button>
        </>
      )}
    </div>
  );
}