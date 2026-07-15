"use client";

import { useEffect } from "react";

export default function Home() {
  useEffect(() => {
    const glyphs = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#%&";

    // ---- Preloader ----
    const pctEl = document.getElementById("pct");
    let pct = 0;
    const loadIv = setInterval(() => {
      pct += Math.floor(Math.random() * 9) + 3;
      if (pct >= 100) {
        pct = 100;
        clearInterval(loadIv);
        if (pctEl) pctEl.textContent = "100%";
        setTimeout(() => {
          document.getElementById("preloader")?.classList.add("done");
        }, 300);
      } else if (pctEl) {
        pctEl.textContent = pct + "%";
      }
    }, 90);


    // ---- Magnetic buttons ----
    document.querySelectorAll(".mbtn").forEach((btn) => {
      const a = btn.querySelector("a") as HTMLElement | null;
      btn.addEventListener("mousemove", (e) => {
        const me = e as MouseEvent;
        const r = btn.getBoundingClientRect();
        const relX = me.clientX - r.left - r.width / 2;
        const relY = me.clientY - r.top - r.height / 2;
        if (a) a.style.transform = `translate(${relX * 0.3}px, ${relY * 0.4}px)`;
      });
      btn.addEventListener("mouseleave", () => {
        if (a) a.style.transform = "translate(0,0)";
      });
    });

    // ---- 3D tilt cards ----
    document.querySelectorAll(".tilt-card").forEach((card) => {
      const el = card as HTMLElement;
      el.addEventListener("mousemove", (e) => {
        const me = e as MouseEvent;
        const r = el.getBoundingClientRect();
        const px = (me.clientX - r.left) / r.width - 0.5;
        const py = (me.clientY - r.top) / r.height - 0.5;
        el.style.transform = `perspective(600px) rotateY(${px * 14}deg) rotateX(${-py * 14}deg) scale(1.03)`;
      });
      el.addEventListener("mouseleave", () => {
        el.style.transform = "perspective(600px) rotateY(0) rotateX(0) scale(1)";
      });
    });

    // ---- Stagger headline reveal ----
    document.querySelectorAll(".stagger-head").forEach((h) => {
      const words = h.textContent?.trim().split(" ") || [];
      h.innerHTML = words.map((w) => `<span class="w">${w}&nbsp;</span>`).join("");
    });
    const staggerObs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            [...entry.target.querySelectorAll(".w")].forEach((w, i) => {
              setTimeout(() => w.classList.add("on"), i * 70);
            });
            staggerObs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.4 }
    );
    document.querySelectorAll(".stagger-head").forEach((h) => staggerObs.observe(h));

    // ---- Counter stats ----
    const counters = document.querySelectorAll(".stat .num");
    const countObs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const el = entry.target as HTMLElement;
            const target = parseInt(el.dataset.count || "0");
            let cur = 0;
            const step = Math.max(1, Math.ceil(target / 20));
            const iv = setInterval(() => {
              cur += step;
              if (cur >= target) {
                cur = target;
                clearInterval(iv);
              }
              el.textContent = String(cur);
            }, 45);
            countObs.unobserve(el);
          }
        });
      },
      { threshold: 0.5 }
    );
    counters.forEach((c) => countObs.observe(c));

    // ---- Cleanup on unmount ----
    return () => {
      clearInterval(loadIv);
      staggerObs.disconnect();
      countObs.disconnect();
    };
  }, []);

  return (
    <>
      <div id="preloader">
        <div className="pct mono" id="pct">0%</div>
        <div className="label">WAKING THE EYES</div>
      </div>
      <svg id="grain" width="0" height="0">
        <filter id="noiseFilter">
          <feTurbulence type="fractalNoise" baseFrequency={0.85} numOctaves={2} stitchTiles="stitch" />
        </filter>
      </svg>
      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 90,
          pointerEvents: "none",
          opacity: 0.045,
          mixBlendMode: "overlay",
          filter: "url(#noiseFilter)",
          background: "#000",
        }}
      ></div>


      <nav>
        <div className="display" style={{ fontWeight: 800 }}>ARGUS</div>
        <div><span className="dot-live"></span>WATCHING</div>
      </nav>

      <section className="hero">
        <div className="blob blob1"></div>
        <div className="blob blob2"></div>
        <div className="hero-eyebrow">GITHUB APP · AGENTIC CODE REVIEW</div>
        <h1 className="hero-title">
          <span className="glitch" data-text="ARGUS">ARGUS</span>
        </h1>
        <p className="hero-sub">
          A multi-agent system that reviews every pull request the second it opens — and writes your
          documentation back when it drifts. No auto-merges. Ever.
        </p>
        <div className="hero-cta">
          <div className="mbtn" id="mbtn1"><a href="#gallery">Meet the agents ↓</a></div>
          <div className="mbtn outline" id="mbtn2"><a href="#">View source</a></div>
        </div>
      </section>

      <div className="marquee-strip">
        <div className="marquee-track">
          <span>PLANNER ROUTES</span><span className="hi">FOUR AGENTS</span>
          <span>ONE CRITIC ARBITRATES</span><span className="hi">DOCS AGENT WRITES BACK</span>
          <span>NEVER AUTO-MERGES</span>
          <span>PLANNER ROUTES</span><span className="hi">FOUR AGENTS</span>
          <span>ONE CRITIC ARBITRATES</span><span className="hi">DOCS AGENT WRITES BACK</span>
          <span>NEVER AUTO-MERGES</span>
        </div>
      </div>

      <section>
        <div className="stats">
          <div className="stat"><div className="num" data-count="4">0</div><div className="lbl">SPECIALIST AGENTS</div></div>
          <div className="stat"><div className="num" data-count="1">0</div><div className="lbl">CRITIC ARBITRATOR</div></div>
          <div className="stat"><div className="num" data-count="2">0</div><div className="lbl">TRIGGER MODES</div></div>
          <div className="stat"><div className="num" data-count="0">0</div><div className="lbl">SELF-MERGES ALLOWED</div></div>
        </div>
      </section>

      <section id="gallery">
        <h2 className="stagger-head" id="galleryHead">Four agents, one pass</h2>
        <p className="section-p">
          Drag sideways. Each one reads the same diff for something different — the critic reconciles
          what they find into a single review.
        </p>
        <div className="gallery-track">
          <div className="tilt-card c1"><div className="glow"></div><div className="num">01 / SECURITY</div><div><h4>Sec</h4><p>Secrets, injection risk, unsafe deserialization — pulls full-file context when needed.</p></div></div>
          <div className="tilt-card c2"><div className="glow"></div><div className="num">02 / LOGIC</div><div><h4>Logic</h4><p>Traces control flow for off-by-ones, null handling, race conditions in async code.</p></div></div>
          <div className="tilt-card c3"><div className="glow"></div><div className="num">03 / STYLE</div><div><h4>Style</h4><p>Checks against conventions inferred from your own repo, not a generic linter.</p></div></div>
          <div className="tilt-card c4"><div className="glow"></div><div className="num">04 / TESTS</div><div><h4>Tests</h4><p>Flags changed logic that shipped without a corresponding test update.</p></div></div>
          <div className="tilt-card c5"><div className="glow"></div><div className="num">05 / CRITIC</div><div><h4>Critic</h4><p>Dedupes findings, ranks severity, resolves disagreements. Ships one clean review.</p></div></div>
        </div>
      </section>

      <section>
        <h2 className="stagger-head" id="modesHead">Two ways it watches</h2>
        <div className="modes-grid">
          <div className="mode-block review">
            <div className="tag mono">01 — REACTIVE</div>
            <h3>Review Mode</h3>
            <p>Fires the moment a PR opens. Runs the specialist agents through the planner, posts inline comments within seconds.</p>
          </div>
          <div className="mode-block docs">
            <div className="tag mono">02 — PROACTIVE</div>
            <h3>Docs Mode</h3>
            <p>Fires after every merge. Detects doc drift, drafts the fix, self-checks it, opens its own PR — and waits for a human.</p>
          </div>
        </div>
      </section>

      <footer>
        <div className="big">Some eyes<br />always stay open.</div>
        <div className="credit">Built by <a href="#">Aman Singh</a> · <a href="#">github.com/AmanSingh-404</a></div>
      </footer>
    </>
  );
}