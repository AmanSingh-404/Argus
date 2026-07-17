"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface DocsPRItem {
  id: number;
  repo_full_name: string;
  doc_path: string;
  pr_number: number | null;
  trigger: string;
  source_commit_sha: string;
  status: string;
  opened_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  opened: "#C6F135",
  failed: "#FF3D9A",
  pending: "#9C93AE",
};

const TRIGGER_LABELS: Record<string, string> = {
  push: "PUSH",
  scheduled: "NIGHTLY SWEEP",
};

export default function DocsPRsPage() {
  const [prs, setPrs] = useState<DocsPRItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/docs-prs`)
      .then((res) => res.json())
      .then((data) => {
        setPrs(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "#0C0910", color: "#F4F1FA", padding: "60px 7vw", fontFamily: "monospace" }}>
      <Link href="/reviews" style={{ color: "#9C93AE", fontSize: 13, textDecoration: "none" }}>
        ← review history
      </Link>

      <h1 style={{ fontSize: 32, margin: "16px 0 6px", fontWeight: 800 }}>Docs Agent — Self-Opened PRs</h1>
      <p style={{ color: "#9C93AE", fontSize: 13, marginBottom: 40 }}>
        Every pull request Argus has opened on its own, with no human triggering it directly.
      </p>

      {loading && <p style={{ color: "#9C93AE" }}>Loading…</p>}
      {!loading && prs.length === 0 && <p style={{ color: "#9C93AE" }}>No self-opened PRs yet.</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: 1, background: "rgba(244,241,250,0.1)" }}>
        {prs.map((p) => (
          <a
            key={p.id}
            href={p.pr_number ? `https://github.com/${p.repo_full_name}/pull/${p.pr_number}` : undefined}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 140px 140px 160px 180px",
              gap: 16,
              alignItems: "center",
              padding: "16px 20px",
              background: "#0C0910",
              color: "#F4F1FA",
              textDecoration: "none",
              fontSize: 13,
            }}
          >
            <span>
              {p.doc_path} {p.pr_number ? <span style={{ color: "#9C93AE" }}>#{p.pr_number}</span> : null}
            </span>
            <span style={{ color: "#9C93AE", fontSize: 11 }}>{TRIGGER_LABELS[p.trigger] || p.trigger}</span>
            <span style={{ color: "#9C93AE", fontSize: 11 }}>{p.source_commit_sha.slice(0, 7)}</span>
            <span style={{ color: STATUS_COLORS[p.status] || "#9C93AE" }}>{p.status}</span>
            <span style={{ color: "#9C93AE", fontSize: 11 }}>{new Date(p.opened_at).toLocaleString()}</span>
          </a>
        ))}
      </div>
    </div>
  );
}