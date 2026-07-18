"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/reviews", label: "Reviews" },
  { href: "/docs-prs", label: "Docs PRs" },
  { href: "/settings", label: "Settings" },
];

export default function DashboardNav() {
  const pathname = usePathname();

  if (pathname === "/") return null; // hide on landing page

  return (
    <div className="dash-nav">
      <div className="dash-nav-left">
        <Link href="/" className="dash-logo">
          <span className="dot-live" />
          ARGUS
        </Link>
        <div className="dash-nav-links">
          {LINKS.map((link) => {
            const isActive = pathname === link.href || pathname.startsWith(link.href + "/");
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`dash-nav-link ${isActive ? "active" : ""}`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      </div>
      <div className="dash-nav-right">WATCHING</div>
    </div>
  );
}