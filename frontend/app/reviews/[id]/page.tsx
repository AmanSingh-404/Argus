"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface Finding {
  file: string;
  line: number;
  severity: string;
  message: string;
  agent?: string;
}

interface AgentRun {
  agent_name: string;
  findings: Finding[];
  duration_ms: number;
}

interface ReviewDetail {
  id: number;
  repo_full_name: string;
  pr_number: number;
  commit_sha: string;
  status: string;
  opened_at: string;
  agent_runs: AgentRun[];
}

const AGENT_COLORS: Record<string, string> = {
  security: "#FF3D9A",
  logic: "#3DE0FF",
  style: "#C6F135",
  tests: "#8B5CF6",
  critic: "#F4F1FA",
};

const SEVERITY_CLASS: Record<string, string> = {
  high: "bad",
  medium: "neutral",
  low: "ok",
};

export default function ReviewDetailPage() {
  const params = useParams();
  const [review, setReview] = useState<ReviewDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/reviews/${params.id}`)
      .then((res) => res.json())
      .then((data) => {
        setReview(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [params.id]);

  if (loading) return <div className="dash"><div className="dash-inner"><div className="dash-loading">Loading…</div></div></div>;
  if (!review) return <div className="dash"><div className="dash-inner"><div className="dash-empty">Review not found.</div></div></div>;

  const specialistRuns = review.agent_runs.filter((ar) => ar.agent_name !== "critic");
  const criticRun = review.agent_runs.find((ar) => ar.agent_name === "critic");

  return (
    <div className="dash">
      <div className="dash-inner">
        <Link href="/reviews" className="mono" style={{ color: "var(--dim)", fontSize: 13, textDecoration: "none", display: "inline-block", marginTop: 32 }}>
          ← back to reviews
        </Link>

        <div className="dash-header" style={{ paddingTop: 20 }}>
          <div className="dash-eyebrow">TRACE VIEW</div>
          <h1 className="dash-h1">{review.repo_full_name} #{review.pr_number}</h1>
          <p className="dash-sub mono">{review.commit_sha.slice(0, 7)} · {review.status}</p>
        </div>

        <div style={{ marginBottom: 16, fontFamily: "'JetBrains Mono'", fontSize: 12, letterSpacing: "0.08em", color: "var(--dim)" }}>
          SPECIALIST AGENTS — before critic
        </div>
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.max(specialistRuns.length, 1)}, 1fr)`, gap: 14, marginBottom: 50 }}>
          {specialistRuns.map((ar) => (
            <div
              key={ar.agent_name}
              className="dash-card dash-card-pad"
              style={{ borderColor: `${AGENT_COLORS[ar.agent_name]}33` }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
                <span className="mono" style={{ color: AGENT_COLORS[ar.agent_name], fontWeight: 700, textTransform: "uppercase", fontSize: 12.5 }}>
                  {ar.agent_name}
                </span>
                <span className="mono" style={{ color: "var(--dim)", fontSize: 11 }}>{(ar.duration_ms / 1000).toFixed(1)}s</span>
              </div>
              {ar.findings.length === 0 && <p className="mono" style={{ color: "var(--dim-2)", fontSize: 12 }}>No findings</p>}
              {ar.findings.map((f, i) => (
                <div key={i} style={{ fontSize: 12, marginBottom: 12, paddingBottom: 12, borderBottom: i < ar.findings.length - 1 ? "1px solid var(--line)" : "none" }}>
                  <div className="mono" style={{ color: "var(--dim)", marginBottom: 4 }}>{f.file}:{f.line} · {f.severity}</div>
                  <div style={{ lineHeight: 1.5 }}>{f.message}</div>
                </div>
              ))}
            </div>
          ))}
        </div>

        {criticRun && (
          <>
            <div style={{ marginBottom: 16, fontFamily: "'JetBrains Mono'", fontSize: 12, letterSpacing: "0.08em", color: "var(--dim)" }}>
              CRITIC — FINAL ARBITRATED REVIEW ({criticRun.findings.length} posted)
            </div>
            <div className="dash-card">
              {criticRun.findings.length === 0 && (
                <div className="dash-card-pad" style={{ color: "var(--dim-2)", fontSize: 13 }}>No issues — clean review posted.</div>
              )}
              {criticRun.findings.map((f, i) => (
                <div key={i} className="dash-card-pad" style={{ borderBottom: i < criticRun.findings.length - 1 ? "1px solid var(--line)" : "none" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <span className={`dash-badge ${SEVERITY_CLASS[f.severity] || "neutral"}`}>{f.severity}</span>
                    <span className="mono" style={{ fontSize: 12.5, color: "var(--dim)" }}>{f.file}:{f.line}</span>
                    <span className="mono" style={{ fontSize: 11, color: AGENT_COLORS[f.agent || ""] || "var(--dim)" }}>
                      flagged by {f.agent}
                    </span>
                  </div>
                  <div style={{ fontSize: 13.5, lineHeight: 1.55 }}>{f.message}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}