# Argus — Autonomous Multi-Agent Code Review System

> *In Greek mythology, Argus Panoptes was a giant with a hundred eyes, tasked as an all-seeing guardian. Argus never truly slept — some eyes always stayed open.*

**One-liner:** Argus is an autonomous agentic system that watches your GitHub repository. It reviews every pull request the moment it's opened, posting structured, context-aware feedback — security flags, logic bugs, style violations, missing test coverage — and it also **maintains your documentation on its own**, opening PRs to update docs whenever code changes make them stale, the way Mintlify's docs agent does.

Two capabilities, one agent platform:
1. **Review mode** (reactive) — comments on PRs humans open
2. **Docs mode** (proactive) — opens its own PRs when it detects documentation drift

---

## 1. Why This Project (Positioning)

Most "AI code review" student projects are a single prompt: *"send the diff to GPT, print the response."* Argus is deliberately not that. It's built to demonstrate three things interviewers actually probe on:

| Claim | How Argus proves it |
|---|---|
| "I can build production backend systems" | Webhooks, queues, idempotency, OAuth Apps, retries |
| "I understand agentic AI, not just prompting" | Dynamic planning, tool-using agents, stateful multi-agent graph, arbitration |
| "I can build agents that *act*, not just comment" | Docs Agent autonomously branches, commits, and opens its own PRs — write access, not just read/comment |
| "I can ship full-stack" | Real dashboard, real DB, real auth, deployed and demoable |

---

## 2. System Architecture

```
                    ┌─────────────────────────┐
GitHub PR Event ──▶ │  Webhook Ingestion API   │  (Express/FastAPI)
(opened/sync)       │  - verifies signature    │
                     │  - enqueues job          │
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────┐
                     │   Redis + BullMQ Queue   │  (async, retry-safe)
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────────────────────┐
                     │        Argus Orchestrator (LangGraph)     │
                     │                                           │
                     │   ┌─────────────┐                         │
                     │   │ Planner Node │ → decides which agents │
                     │   └──────┬──────┘   should run on this PR │
                     │          ▼                                │
                     │  ┌──────────┬──────────┬──────────┐       │
                     │  │ Security │  Logic/   │  Style/  │       │
                     │  │  Agent   │   Bug     │Convention│  ...  │
                     │  │          │  Agent    │  Agent   │       │
                     │  └────┬─────┴────┬──────┴────┬─────┘       │
                     │       └──────────┼───────────┘             │
                     │                  ▼                         │
                     │         ┌──────────────────┐               │
                     │         │  Critic/Aggregator │              │
                     │         │  - dedupes         │              │
                     │         │  - ranks severity  │              │
                     │         │  - resolves conflicts│            │
                     │         └────────┬───────────┘              │
                     └──────────────────┼──────────────────────────┘
                                        ▼
                          ┌──────────────────────────┐
                          │   GitHub API Writer       │
                          │  - inline review comments │
                          │  - PR summary comment     │
                          │  - status check (pass/fail)│
                          └──────────────────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │  Postgres (run history)   │
                          └───────────┬──────────────┘
                                      ▼
                          ┌──────────────────────────┐
                          │  Next.js Dashboard        │
                          │  - review history         │
                          │  - agent reasoning traces  │
                          │  - repo health analytics   │
                          │  - docs PR history         │
                          └──────────────────────────┘
```

### Second trigger path: the Docs Agent (proactive, not reactive)

This runs on a **different trigger** than the review flow — it fires on `push` to the default branch (i.e., after a PR merges), not on PR-open. It's a separate LangGraph flow that ends in Argus opening its *own* PR rather than commenting on someone else's.

```
Push to main (PR merged)
        │
        ▼
Diff since last docs run ──▶ Docs Agent
                                 │
                    ┌────────────┴─────────────┐
                    │ 1. Identify affected docs  │  (maps changed source files
                    │    (route/API/config maps  │   → corresponding doc pages
                    │    to doc pages)            │   via a repo-specific index)
                    ├────────────────────────────┤
                    │ 2. Draft doc updates        │  (rewrites the stale section,
                    │    (LLM generation)          │   not the whole page)
                    ├────────────────────────────┤
                    │ 3. Self-check pass           │  (re-reads generated docs
                    │    against source of truth)  │   against the actual code diff)
                    └────────────┬────────────────┘
                                 ▼
                    Create branch → commit → open PR
                    ("docs: update API reference for
                      /auth endpoint changes")
                                 │
                                 ▼
                    Tag repo maintainer as reviewer
                    (Argus never auto-merges its own PRs)
```

---

## 3. The Agent Layer (the actual "Agentic AI" part)

This is what separates Argus from a wrapper. Each node in the LangGraph graph is a real decision point, not a fixed pipeline stage.

### Planner Agent
Reads the PR metadata (files changed, size, labels, which directories touched) and **decides which specialist agents are worth running**. A 3-line README typo fix should not trigger the Security Agent. A new auth middleware file should trigger Security + Logic, and probably skip Style. This routing logic is your strongest "this is actually agentic" talking point — it's a policy decision, not a hardcoded if-else.

### Specialist Agents (each with distinct tools + prompts)
- **Security Agent** — scans for injected secrets, unsafe deserialization, SQL/command injection patterns, missing input validation. Tool access: can pull the *full file* (not just the diff hunk) via GitHub API to see surrounding context, since vulnerabilities often depend on code outside the changed lines.
- **Logic/Bug Agent** — traces control flow for off-by-one errors, null/undefined handling, race conditions in async code, unreachable branches.
- **Style/Convention Agent** — checks against repo-specific conventions (naming, import order, error-handling patterns) inferred from a sample of existing files in the repo, not a generic linter.
- **Test Coverage Agent** — cross-references changed source files against the test directory; flags logic changes with no corresponding test update.

### Critic / Aggregator Agent
Receives all specialist outputs as shared state. Its job: **arbitration**, not concatenation.
- Deduplicates overlapping findings (Security and Logic agents often flag the same line for different reasons)
- Ranks by severity (blocking vs. nit)
- Resolves disagreements (e.g., Style Agent suggests a pattern that Security Agent flags as unsafe — Critic decides which wins)
- Produces the final structured output that gets posted to GitHub

### Docs Agent (the Mintlify-style piece)
Unlike the review specialists, this agent doesn't just read and report — it **writes to the repo**. It runs on a separate trigger (post-merge push to main, or a scheduled nightly sweep) and follows a distinct three-step loop:

1. **Drift detection** — maintains a lightweight index mapping source files (routes, API handlers, config schemas, public function signatures) to the doc pages that describe them. When a mapped source file changes, the corresponding doc page is flagged as potentially stale.
2. **Targeted generation** — rewrites only the affected section of the doc, not the whole page. This keeps diffs small and review-friendly (a maintainer should be able to review a docs PR in under a minute).
3. **Self-check pass** — before opening the PR, a second pass re-reads its own generated docs against the actual code diff and flags low-confidence claims rather than shipping them. This mirrors the Critic pattern from the review flow: generate, then verify, don't just generate.

**Guardrail (important for the demo and for real safety):** Argus never auto-merges its own PRs. Every docs PR is opened as a normal PR, tagged to a human reviewer, and goes through the exact same CI/review process as any other PR — including, notably, Argus's own Review mode reviewing it. That's a nice detail to point out live: *the review agent reviews the docs agent's PRs.*

### Why LangGraph specifically (talking point)
State persists across the graph run — later agents can see earlier agents' findings, which avoids redundant comments and lets the Critic reason over the *set* of findings rather than isolated outputs. This is the difference you'd explain in an interview between "agentic system" and "four parallel API calls."

---

## 4. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration | **LangGraph** (Python) | Native support for stateful multi-agent graphs, checkpointing, conditional routing |
| LLM | **Gemini API** (or Claude API) | You already have Gemini experience from CollabIQ/CrashBoard |
| Backend/Webhook | **FastAPI** (Python) | Keeps ingestion + orchestration in one language, avoids a Node↔Python bridge |
| Queue | **Redis + BullMQ** or Python **Celery** | Webhook bursts (someone pushes 10 commits fast) need async, retry-safe processing |
| Database | **PostgreSQL** | Review runs, agent traces, PR metadata, repo settings |
| Auth | **GitHub OAuth App** (not a raw PAT) | Real installation-token flow, scoped permissions — shows you understand GitHub's actual integration model |
| Frontend | **Next.js 14 + TypeScript + Tailwind** | Matches your CollabIQ/CrashBoard stack |
| Git operations | **GitHub API (Git Data API)** — branch creation, tree/blob commits, PR creation | Docs Agent needs real write access, not just comments |
| Scheduler | **BullMQ repeatable jobs** (or cron) | Triggers the nightly docs-drift sweep independent of push events |
| Deployment | **Railway/Render** (backend) + **Vercel** (frontend) | You've used both before |

> Decision point: keep backend fully in Python (FastAPI) since LangGraph is Python-native — avoids maintaining orchestration logic in a second language. Use Next.js purely for the dashboard, talking to FastAPI over REST.

---

## 5. Data Model (core tables)

```
repos            (id, github_repo_id, owner, name, installed_at, settings_json)
pr_reviews       (id, repo_id, pr_number, status, opened_at, completed_at)
agent_runs       (id, review_id, agent_name, input_summary, output_json, duration_ms)
findings         (id, review_id, agent_name, file_path, line, severity, message, resolved_by_critic)

doc_index        (id, repo_id, source_path, doc_path, last_synced_commit_sha)
docs_prs         (id, repo_id, pr_number, trigger, source_commit_sha, status, opened_at)
```

`agent_runs` is what makes the dashboard's "reasoning trace" view possible — you can replay exactly what each agent saw and concluded, which is a great live demo moment. `doc_index` is the mapping table the Docs Agent uses to know which doc page maps to which source file; `docs_prs` tracks every PR Argus has opened on its own (`trigger` is `push` or `scheduled`).

---

## 6. Dashboard Features (Next.js)

1. **Review history** — list of PRs reviewed, pass/fail status, time taken
2. **Agent trace view** — click into a review, see each agent's individual findings before Critic arbitration (this visually proves the multi-agent architecture — don't skip this)
3. **Repo analytics** — findings-per-PR trend, most common issue categories over time
4. **Settings** — toggle which agents are active per repo, severity thresholds for blocking merges
5. **Docs PR history** — every PR Argus has opened autonomously, with a diff preview, what triggered it (a specific merge vs. the nightly sweep), and merge status — this is the section that visually sells "this agent acts, not just comments"

---

## 7. Build Order (avoid over-scoping)

1. **Week 1** — Webhook → Postgres → single hardcoded agent (Security) → posts one GitHub comment. Get the full loop working end-to-end before anything else.
2. **Week 2** — Introduce LangGraph, replace the hardcoded call with Planner → Security only, prove routing logic works.
3. **Week 3** — Add remaining specialist agents in parallel branches + Critic aggregation.
4. **Week 4** — Queue layer (Redis/BullMQ) for async + retry handling; GitHub OAuth App proper install flow.
5. **Week 5** — Dashboard: review history + agent trace view (this is the demo centerpiece).
6. **Week 6** — Docs Agent: drift detection index, targeted generation, self-check pass, branch/commit/PR creation via Git Data API.
7. **Week 7** — Wire the scheduler (nightly sweep) + docs PR history view in the dashboard.
8. **Week 8** — Polish: analytics page, deploy, record a demo video, write the README/architecture doc.

> If you're time-boxed, Review mode alone is a complete, demoable project — treat the Docs Agent (weeks 6–7) as the extension that pushes this from "solid" to "standout." Build and ship Review mode first.

---

## 8. Resume Bullet (draft)

> **Argus — Autonomous Multi-Agent Code Review & Documentation System** *(LangGraph, FastAPI, Next.js, PostgreSQL, GitHub OAuth)*
> Built an agentic system that autonomously reviews GitHub PRs using a dynamically-routed multi-agent graph (Planner → 4 specialist agents → Critic arbitration) and independently maintains repo documentation, detecting doc drift from merged commits and opening its own PRs with self-verified updates via GitHub's Git Data API. Processes events asynchronously via Redis/BullMQ with retry handling; dashboard visualizes per-agent reasoning traces, review analytics, and autonomously-opened documentation PRs.

---

## 9. Interview Questions You Should Be Ready For

- "Why LangGraph over just chaining API calls?" → state persistence, conditional routing, checkpointing for long-running graphs
- "How do you handle context window limits on large diffs?" → chunking strategy, only pulling full-file context when the Security agent specifically needs it
- "How do you avoid the LLM hallucinating a vulnerability that doesn't exist?" → talk about how you'd tune prompts/confidence thresholds, and that Critic agent's job includes filtering low-confidence findings
- "What happens if GitHub sends duplicate webhook events?" → idempotency key on `(repo_id, pr_number, commit_sha)` in `pr_reviews`
- "How would this scale to 1000s of repos?" → queue-based decoupling, per-repo rate limiting against GitHub API limits, caching unchanged file content between review runs on the same PR
- "How does the Docs Agent know which docs correspond to which code?" → the `doc_index` mapping table, built once per repo (either from a config file convention or an initial LLM pass over the repo structure), then incrementally updated
- "What stops the Docs Agent from writing wrong or hallucinated documentation?" → the self-check pass re-verifies generated text against the actual diff before opening the PR; low-confidence claims are flagged inline in the PR description rather than stated as fact; and critically, it never auto-merges — a human always reviews
- "Why not just auto-merge docs PRs since they're 'low risk'?" → good question to have an opinion on: even low-risk automated changes should have a human checkpoint, especially early in the project's life — this is a deliberate safety/trust design choice, not a limitation
