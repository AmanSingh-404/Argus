# Argus

**A multi-agent system that reviews GitHub pull requests and keeps your documentation in sync — both without you asking.**

Argus runs in two modes:

1. **Review Mode** (reactive) — the moment a PR opens, a planner routes it to the right specialist agents (Security, Logic, Style, Tests), which run in parallel and report to a Critic that arbitrates conflicts and posts one clean review.
2. **Docs Mode** (proactive) — after every merge, Argus checks whether the change makes any indexed documentation stale, drafts a fix, verifies its own draft against the actual diff, and opens a real pull request — which it never merges itself.

---

## Why this exists

Most "AI code review" projects are a single prompt wrapping an LLM call. Argus is deliberately not that. It's built around three things:

- **Real orchestration** — a LangGraph graph with a Planner that dynamically decides which agents run based on what actually changed and per-repo settings, not a fixed pipeline.
- **Real arbitration** — a Critic that dedupes overlapping findings across agents and resolves conflicts by severity, rather than concatenating four opinions.
- **Real autonomy, with a leash** — the Docs Agent writes to the repo (branches, commits, PRs) on its own, but never merges its own work, and its own drafts get independently self-checked against the diff before anything is opened.

---

## Architecture

```
GitHub PR opened ─────────► Webhook ─► Celery Queue ─► LangGraph
                                                          │
                                                    ┌─────┴─────┐
                                                 Planner   (decides which
                                                    │       agents to run,
                                                    │       respecting per-repo
                                                    │       settings)
                                       ┌────────────┼────────────┬─────────┐
                                   Security       Logic        Style      Tests
                                       └────────────┴────────────┴─────────┘
                                                    │
                                                 Critic
                                          (dedupe + arbitrate)
                                                    │
                                          Inline review posted to GitHub


GitHub push to main ───────► Webhook ─► Celery Queue ─► Docs Agent
                                                          │
                                                  Check doc_index for
                                                  affected doc pages
                                                          │
                                                  Draft targeted update
                                                          │
                                                  Self-check against diff
                                                          │
                                              confident? ─┴─ not confident?
                                                  │              │
                                          Branch, commit,      Skip, log
                                          open PR (never       as failed
                                          auto-merged)

                             (also runs nightly via Celery Beat,
                              independent of any specific push,
                              with a dedup guard against
                              already-open PRs)
```

**Stack:** FastAPI · LangGraph · Celery + Redis · PostgreSQL · Gemini API · Next.js 14 · GitHub App (webhooks, installation auth, Git Data API)

---

## The agents

**Planner** — reads which files changed in a PR, plus per-repo settings, and decides which specialists are worth running. A `.md`-only change skips the code agents entirely; a change touching auth/config files always triggers Security. This is a real runtime decision, logged and inspectable per-review in the dashboard.

**Security** — flags hardcoded secrets, injection risk, unsafe deserialization, missing input validation. Pulls full-file context via the GitHub API when the diff hunk alone isn't enough to judge.

**Logic** — traces control flow for off-by-ones, incorrect null handling, race conditions in async code.

**Style** — checks against conventions inferred from the repo's own existing files, not a generic linter config nobody agreed to.

**Tests** — cross-references changed source files against the test directory, flagging logic changes that shipped without corresponding test updates.

**Critic** — takes every specialist's raw output, dedupes findings that land on the same file+line (keeping the higher severity), and produces the single review that actually gets posted. This is the piece that makes it "one clean review" instead of four agents talking over each other.

**Docs Agent** — a separate two-step LLM pipeline (draft, then independently self-check the draft against the real diff) that only proceeds to open a PR when the self-check is genuinely confident — enforced in code, not just prompted. It has full write access to the repo but is deliberately never allowed to merge its own work.

---

## What it actually looks like

A real Security finding, posted inline on the exact line:

> 🔴 **SECURITY · high**
> SQL injection vulnerability due to direct string formatting of `user_id` parameter into the SQL query.
> — flagged by security-agent, confirmed by critic

A real self-opened docs PR:

> **docs: update docs/api.md to match app.py** — opened by `arguscore[bot]`
> Argus detected that recent changes to `app.py` may have made `docs/api.md` outdated, and drafted this update.
> This PR was opened automatically and has not been merged — please review before merging.

*(Screenshots go in `/docs/screenshots` — see "Adding screenshots" below)*

---

## Dashboard

- **`/reviews`** — history of every PR reviewed, with a findings-per-PR chart
- **`/reviews/[id]`** — the trace view: each specialist agent's raw findings side by side, before Critic arbitration, plus the final posted output
- **`/docs-prs`** — every PR the Docs Agent has opened on its own, with an inline, color-coded diff preview of the source change that triggered it
- **`/settings`** — per-repo toggles for each agent, which genuinely change what the Planner routes to at runtime (not cosmetic — proven by disabling an agent and confirming it stops running)

---

## Local setup

### 1. Infra
```bash
docker-compose up -d
```

### 2. Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # fill in GitHub App + Gemini credentials
python create_tables.py
uvicorn app.main:app --reload --port 8000
```

In a second terminal, the background worker:
```bash
celery -A app.celery_app worker --pool=solo --loglevel=info   # --pool=solo needed on Windows
```

And a third, for the scheduled docs-drift sweep:
```bash
celery -A app.celery_app beat --loglevel=info
```

### 3. Frontend
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

### 4. Expose your local server
GitHub needs a public URL to send webhooks to:
```bash
ngrok http 8000
```
Set the resulting URL as your GitHub App's webhook URL: `<ngrok-url>/webhooks/github`

### 5. GitHub App setup
Create a GitHub App with:
- **Permissions:** Pull requests (read/write), Contents (read/write), Metadata (read-only)
- **Subscribe to events:** Pull request, Push, Installation
- Generate a private key, point `GITHUB_APP_PRIVATE_KEY_PATH` at it
- Install it on a test repository

---

## Adding screenshots

To finish this README before sharing it:
1. Take screenshots of: a real inline Security finding on GitHub, the `/reviews/[id]` trace view, a real self-opened docs PR, and the `/docs-prs` diff preview.
2. Save them into `docs/screenshots/`.
3. Replace the placeholder line above with actual `![...]()` image embeds.

A 2-3 minute demo video (open a PR → watch the review land → merge a change → watch a docs PR appear) is worth more than any number of screenshots — record one if you can.

---

## Known limitations

- **Not deployed** — currently runs against local Postgres/Redis via Docker Compose and a local FastAPI/Celery process, tunneled through ngrok. Deployment (Railway/Render + Vercel) is a deliberate next step, not an oversight.
- **Single-repo assumptions in places** — the nightly sweep and one-time indexer currently reference one hardcoded installation. The `repos` table exists and is populated correctly from real installation events, but not every code path reads from it yet.
- **Doc indexing is a one-time LLM pass** — it doesn't automatically re-index if a repo's structure changes significantly; re-running the indexer is a manual step for now.

---

## Build story

This was built in phases, each ending in a working, demoable checkpoint before moving to the next — Review Mode (Phases 0-6) first, proven complete and working end-to-end, then the Docs Agent (Phase 7) and its scheduler/dashboard (Phase 8) as a deliberate extension once the core was solid.

A few of the real bugs hit and fixed along the way, if you're curious what actually went wrong building this:
- A Gemini model ID that got deprecated mid-project, caught via a live 404 during testing
- A three-way port conflict between two native Postgres installs and Docker, diagnosed via `netstat`/`tasklist`
- A blocking LLM call silently serializing four "parallel" agents — fixed with `asyncio.to_thread`, verified by comparing before/after timestamps (68s → 30s)
- A GitHub Apps permissions-approval gate that silently blocked new event types from ever firing, despite the webhook subscription showing as saved
- A self-check LLM call that contradicted its own stated confidence — caught, root-caused as token truncation, and hardened with a code-level consistency guard rather than trusting the prompt alone
- Genuine dead code after an unreachable `return` statement, silently swallowing an entire webhook handler

Each of these is logged in the commit history at the point it was fixed.