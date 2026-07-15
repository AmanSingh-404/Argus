"use client";

import { useEffect } from "react";

export default function CustomCursor() {
  useEffect(() => {
    const dot = document.getElementById("cursorDot");
    const ring = document.getElementById("cursorRing");
    if (!dot || !ring) return;

    let mx = window.innerWidth / 2;
    let my = window.innerHeight / 2;
    let rx = mx;
    let ry = my;
    let hasMoved = false;

    // Initially hide the custom cursor elements until mouse moves
    dot.style.opacity = "0";
    ring.style.opacity = "0";

    const onMove = (e: MouseEvent) => {
      if (!hasMoved) {
        hasMoved = true;
        dot.style.opacity = "1";
        ring.style.opacity = "1";
      }
      mx = e.clientX;
      my = e.clientY;
      dot.style.left = mx + "px";
      dot.style.top = my + "px";
    };

    window.addEventListener("mousemove", onMove);

    let rafId: number;
    function loop() {
      rx += (mx - rx) * 0.18;
      ry += (my - ry) * 0.18;
      if (ring) {
        ring.style.left = rx + "px";
        ring.style.top = ry + "px";
      }
      rafId = requestAnimationFrame(loop);
    }
    loop();

    const onMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      if (target.closest("a, button, [role='button'], .tilt-card, .mbtn, input, select, textarea")) {
        ring.classList.add("hover");
      } else {
        ring.classList.remove("hover");
      }
    };

    window.addEventListener("mouseover", onMouseOver);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseover", onMouseOver);
      cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <>
      <div
        className="cursor-ring"
        id="cursorRing"
        style={{
          transition: "width 0.25s, height 0.25s, border-color 0.25s, background 0.25s, opacity 0.15s",
        }}
      ></div>
      <div
        className="cursor-dot"
        id="cursorDot"
        style={{
          transition: "opacity 0.15s",
        }}
      ></div>
    </>
  );
}
