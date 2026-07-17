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

export default function ReviewsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsPoint[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
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
    <div style={{ minHeight: "100vh", background: "#0C0910", color: "#F4F1FA", padding: "60px 7vw", fontFamily: "monospace" }}>
      <h1 style={{ fontSize: 32, marginBottom: 30, fontWeight: 800 }}>Review History</h1>

      {loading && <p style={{ color: "#9C93AE" }}>Loading…</p>}
      {!loading && reviews.length === 0 && <p style={{ color: "#9C93AE" }}>No reviews yet.</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: 1, background: "rgba(244,241,250,0.1)" }}>
        {reviews.map((r) => (
          <Link
            key={r.id}
            href={`/reviews/${r.id}`}
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "16px 20px",
              background: "#0C0910",
              color: "#F4F1FA",
              textDecoration: "none",
              fontSize: 14,
            }}
          >
            <span>{r.repo_full_name} #{r.pr_number}</span>
            <span style={{ color: r.status === "completed" ? "#C6F135" : r.status === "failed" ? "#FF3D9A" : "#9C93AE" }}>
              {r.status}
            </span>
            <span style={{ color: "#9C93AE" }}>{new Date(r.opened_at).toLocaleString()}</span>
          </Link>
        ))}
      </div>
      {analytics.length > 0 && (
        <div style={{ marginTop: 50 }}>
          <h2 style={{ fontSize: 16, color: "#9C93AE", marginBottom: 20 }}>Findings per PR over time</h2>
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
                    fill={a.finding_count > 0 ? "#C6F135" : "#2a2a35"}
                    rx={3}
                  />
                  <text x={i * 50 + 22} y={128} fontSize="10" fill="#9C93AE" textAnchor="middle">
                    #{a.pr_number}
                  </text>
                  <text x={i * 50 + 22} y={110 - barHeight - 6} fontSize="10" fill="#F4F1FA" textAnchor="middle">
                    {a.finding_count}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      )}
    </div>
  );
}