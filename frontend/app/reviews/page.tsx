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

export default function ReviewsPage() {
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
    </div>
  );
}