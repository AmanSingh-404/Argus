"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Review {
  id: number;
  repo_full_name: string;
  pr_number: number;
  commit_sha: string;
  status: string;
  opened_at: string;
  completed_at: string | null;
}

interface AnalyticsPoint {
  pr_number: number;
  opened_at: string;
  finding_count: number;
}

const STATUS_CLASS: Record<string, string> = {
  completed: "ok",
  failed: "bad",
  pending: "neutral",
  running: "neutral",
};

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/reviews`)
      .then((res) => res.json())
      .then((data) => {
        setReviews(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/analytics/findings-over-time`)
      .then((res) => res.json())
      .then((data) => setAnalytics(data))
      .catch(() => {});
  }, []);

  return (
    <div className="dash">
      <div className="dash-inner">
        <div className="dash-header">
          <div className="dash-eyebrow">REVIEW MODE</div>
          <h1 className="dash-h1">Review History</h1>
          <p className="dash-sub">Every pull request Argus has reviewed, with the specialist agents that ran and what the critic decided.</p>
        </div>

        {loading && <div className="dash-loading">Loading…</div>}
        {!loading && reviews.length === 0 && <div className="dash-empty">No reviews yet — open a PR on a repo with Argus installed.</div>}

        {!loading && reviews.length > 0 && (
          <div className="dash-card">
            {reviews.map((r) => (
              <Link key={r.id} href={`/reviews/${r.id}`} className="dash-row" style={{ gridTemplateColumns: "1fr 140px 200px" }}>
                <span className="mono" style={{ fontSize: 13.5 }}>
                  {r.repo_full_name} <span style={{ color: "var(--dim)" }}>#{r.pr_number}</span>
                </span>
                <span className={`dash-badge ${STATUS_CLASS[r.status] || "neutral"}`}>{r.status}</span>
                <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
                  {new Date(r.opened_at).toLocaleString()}
                </span>
              </Link>
            ))}
          </div>
        )}

        {analytics.length > 0 && (
          <div style={{ marginTop: 50 }}>
            <div className="dash-eyebrow">ANALYTICS</div>
            <h2 style={{ fontFamily: "'Unbounded'", fontSize: 18, fontWeight: 700, marginBottom: 24 }}>
              Findings per PR over time
            </h2>
            <div className="dash-card dash-card-pad">
              <svg width="100%" height="140" viewBox={`0 0 ${analytics.length * 50} 140`} style={{ overflow: "visible" }}>
                {analytics.map((a, i) => {
                  const maxCount = Math.max(...analytics.map((x) => x.finding_count), 1);
                  const barHeight = (a.finding_count / maxCount) * 100;
                  return (
                    <g key={a.pr_number}>
                      <rect
                        x={i * 50 + 10}
                        y={110 - barHeight}
                        width={24}
                        height={Math.max(barHeight, 2)}
                        fill={a.finding_count > 0 ? "var(--lime)" : "#2a2a35"}
                        rx={3}
                      />
                      <text x={i * 50 + 22} y={128} fontSize="10" fill="var(--dim)" textAnchor="middle">
                        #{a.pr_number}
                      </text>
                      <text x={i * 50 + 22} y={110 - barHeight - 6} fontSize="10" fill="var(--ink)" textAnchor="middle">
                        {a.finding_count}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}