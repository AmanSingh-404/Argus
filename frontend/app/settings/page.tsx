"use client";

import { useEffect, useState } from "react";

interface RepoSettings {
  id: number;
  full_name: string;
  security_agent_enabled: boolean;
  logic_agent_enabled: boolean;
  style_agent_enabled: boolean;
  tests_agent_enabled: boolean;
  docs_agent_enabled: boolean;
}

const AGENTS: { key: keyof RepoSettings; label: string; color: string }[] = [
  { key: "security_agent_enabled", label: "Security", color: "#FF3D9A" },
  { key: "logic_agent_enabled", label: "Logic", color: "#3DE0FF" },
  { key: "style_agent_enabled", label: "Style", color: "#C6F135" },
  { key: "tests_agent_enabled", label: "Tests", color: "#8B5CF6" },
  { key: "docs_agent_enabled", label: "Docs Agent", color: "#F0A537" },
];

export default function SettingsPage() {
  const [repos, setRepos] = useState<RepoSettings[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/repos`)
      .then((res) => res.json())
      .then((data) => {
        setRepos(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggle = async (repo: RepoSettings, key: keyof RepoSettings) => {
    const newValue = !repo[key];
    setRepos((prev) => prev.map((r) => (r.id === repo.id ? { ...r, [key]: newValue } : r)));
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/repos/${repo.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [key]: newValue }),
    });
  };

  return (
    <div className="dash">
      <div className="dash-inner">
        <div className="dash-header">
          <div className="dash-eyebrow">CONFIGURATION</div>
          <h1 className="dash-h1">Settings</h1>
          <p className="dash-sub">Toggle which agents run per repo — this changes what the planner routes to in real time.</p>
        </div>

        {loading && <div className="dash-loading">Loading…</div>}

        {repos.map((repo) => (
          <div key={repo.id} className="dash-card dash-card-pad">
            <div className="mono" style={{ fontSize: 14, fontWeight: 700, marginBottom: 20 }}>{repo.full_name}</div>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              {AGENTS.map((agent) => {
                const enabled = repo[agent.key] as boolean;
                return (
                  <button
                    key={agent.key}
                    onClick={() => toggle(repo, agent.key)}
                    className={`dash-pill ${enabled ? "on" : ""}`}
                    style={{ "--pill-color": agent.color } as React.CSSProperties}
                  >
                    <span className="dot" />
                    {agent.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}