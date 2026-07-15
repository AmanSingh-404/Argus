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

  if (loading) return <div style={{ background: "#0C0910", minHeight: "100vh", color: "#9C93AE", padding: 60, fontFamily: "monospace" }}>Loading…</div>;
  if (!review) return <div style={{ background: "#0C0910", minHeight: "100vh", color: "#FF3D9A", padding: 60, fontFamily: "monospace" }}>Review not found.</div>;

  const specialistRuns = review.agent_runs.filter((ar) => ar.agent_name !== "critic");
  const criticRun = review.agent_runs.find((ar) => ar.agent_name === "critic");

  return (
    <div style={{ minHeight: "100vh", background: "#0C0910", color: "#F4F1FA", padding: "50px 7vw", fontFamily: "monospace" }}>
      <Link href="/reviews" style={{ color: "#9C93AE", fontSize: 13, textDecoration: "none" }}>← back to reviews</Link>

      <h1 style={{ fontSize: 28, margin: "16px 0 6px", fontWeight: 800 }}>
        {review.repo_full_name} #{review.pr_number}
      </h1>
      <p style={{ color: "#9C93AE", fontSize: 13, marginBottom: 40 }}>
        {review.commit_sha.slice(0, 7)} · {review.status}
      </p>

      <h2 style={{ fontSize: 15, color: "#9C93AE", marginBottom: 16, letterSpacing: "0.06em" }}>
        SPECIALIST AGENTS (before critic)
      </h2>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.max(specialistRuns.length, 1)}, 1fr)`, gap: 16, marginBottom: 50 }}>
        {specialistRuns.map((ar) => (
          <div key={ar.agent_name} style={{ border: `1px solid ${AGENT_COLORS[ar.agent_name] || "#333"}33`, borderRadius: 12, padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
              <span style={{ color: AGENT_COLORS[ar.agent_name] || "#fff", fontWeight: 700, textTransform: "uppercase", fontSize: 13 }}>
                {ar.agent_name}
              </span>
              <span style={{ color: "#9C93AE", fontSize: 11 }}>{(ar.duration_ms / 1000).toFixed(1)}s</span>
            </div>
            {ar.findings.length === 0 && <p style={{ color: "#5a5568", fontSize: 12 }}>No findings</p>}
            {ar.findings.map((f, i) => (
              <div key={i} style={{ fontSize: 12, marginBottom: 10, paddingBottom: 10, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ color: "#9C93AE" }}>{f.file}:{f.line} · {f.severity}</div>
                <div style={{ marginTop: 4 }}>{f.message}</div>
              </div>
            ))}
          </div>
        ))}
      </div>

      {criticRun && (
        <>
          <h2 style={{ fontSize: 15, color: "#9C93AE", marginBottom: 16, letterSpacing: "0.06em" }}>
            CRITIC — FINAL ARBITRATED REVIEW ({criticRun.findings.length} posted)
          </h2>
          <div style={{ border: "1px solid rgba(244,241,250,0.2)", borderRadius: 12, padding: 20 }}>
            {criticRun.findings.length === 0 && <p style={{ color: "#5a5568", fontSize: 13 }}>No issues — clean review posted.</p>}
            {criticRun.findings.map((f, i) => (
              <div key={i} style={{ fontSize: 13, marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                <div style={{ color: AGENT_COLORS[f.agent || ""] || "#9C93AE" }}>
                  {f.file}:{f.line} · {f.severity} · flagged by {f.agent}
                </div>
                <div style={{ marginTop: 4 }}>{f.message}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}