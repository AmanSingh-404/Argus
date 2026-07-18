"use client";

import { useEffect, useState } from "react";

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

const STATUS_CLASS: Record<string, string> = {
  opened: "ok",
  failed: "bad",
  pending: "neutral",
};

const TRIGGER_LABELS: Record<string, string> = {
  push: "PUSH",
  scheduled: "NIGHTLY SWEEP",
};

export default function DocsPRsPage() {
  const [prs, setPrs] = useState<DocsPRItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [diffs, setDiffs] = useState<Record<number, string>>({});

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/docs-prs`)
      .then((res) => res.json())
      .then((data) => {
        setPrs(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggleDiff = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    if (!diffs[id]) {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/docs-prs/${id}/diff`);
      const data = await res.json();
      setDiffs((prev) => ({ ...prev, [id]: data.diff || data.error || "No diff available" }));
    }
  };

  return (
    <div className="dash">
      <div className="dash-inner">
        <div className="dash-header">
          <div className="dash-eyebrow">DOCS MODE</div>
          <h1 className="dash-h1">Self-Opened Pull Requests</h1>
          <p className="dash-sub">Every PR Argus has opened on its own — no human triggering it directly.</p>
        </div>

        {loading && <div className="dash-loading">Loading…</div>}
        {!loading && prs.length === 0 && <div className="dash-empty">No self-opened PRs yet.</div>}

        {!loading && prs.length > 0 && (
          <div className="dash-card">
            {prs.map((p) => (
              <div key={p.id}>
                <div
                  onClick={() => toggleDiff(p.id)}
                  className="dash-row"
                  style={{ gridTemplateColumns: "20px 1fr 130px 90px 100px 180px" }}
                >
                  <span className={`dash-chevron ${expandedId === p.id ? "open" : ""}`}>›</span>
                  <span className="mono" style={{ fontSize: 13.5 }}>
                    {p.doc_path} {p.pr_number && <span style={{ color: "var(--dim)" }}>#{p.pr_number}</span>}
                  </span>
                  <span className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>{TRIGGER_LABELS[p.trigger] || p.trigger}</span>
                  <span className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>{p.source_commit_sha.slice(0, 7)}</span>
                  <span className={`dash-badge ${STATUS_CLASS[p.status] || "neutral"}`}>{p.status}</span>
                  <span className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>{new Date(p.opened_at).toLocaleString()}</span>
                </div>
                {expandedId === p.id && (
                  <div className="dash-diff">
                    {(diffs[p.id] || "Loading…").split("\n").map((line, i) => (
                      <div
                        key={i}
                        className={`dash-diff-line ${line.startsWith("+") ? "add" : line.startsWith("-") ? "del" : "ctx"}`}
                      >
                        {line}
                      </div>
                    ))}
                    {p.pr_number && (
                      <a
                        href={`https://github.com/${p.repo_full_name}/pull/${p.pr_number}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="dash-btn"
                        style={{ marginTop: 16 }}
                      >
                        View full PR on GitHub →
                      </a>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}