"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

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
    <div style={{ minHeight: "100vh", background: "#0C0910", color: "#F4F1FA", padding: "60px 7vw", fontFamily: "monospace" }}>
      <Link href="/reviews" style={{ color: "#9C93AE", fontSize: 13, textDecoration: "none" }}>
        ← review history
      </Link>

      <h1 style={{ fontSize: 32, margin: "16px 0 40px", fontWeight: 800 }}>Settings</h1>

      {loading && <p style={{ color: "#9C93AE" }}>Loading…</p>}

      {repos.map((repo) => (
        <div key={repo.id} style={{ border: "1px solid rgba(244,241,250,0.1)", borderRadius: 12, padding: 24, marginBottom: 20 }}>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>{repo.full_name}</div>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            {AGENTS.map((agent) => {
              const enabled = repo[agent.key] as boolean;
              return (
                <button
                  key={agent.key}
                  onClick={() => toggle(repo, agent.key)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "10px 16px",
                    borderRadius: 8,
                    border: `1px solid ${enabled ? agent.color : "rgba(244,241,250,0.15)"}`,
                    background: enabled ? `${agent.color}15` : "transparent",
                    color: enabled ? agent.color : "#9C93AE",
                    fontFamily: "monospace",
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: enabled ? agent.color : "#3a3a3a" }} />
                  {agent.label}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}