"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/lib/auth-context";

import { LogOutIcon } from "./icons";
import { Wordmark } from "./Wordmark";
import { buttonSecondary, focusRing } from "./ui";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).map((p) => p[0]!.toUpperCase()).join("") || "?";
}

const NAV = [{ href: "/prompts", label: "Library" }];

/** Header + main region for authenticated pages. */
export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname() ?? "";

  return (
    <div className="flex min-h-full flex-col">
      <a
        href="#main"
        className={`sr-only rounded-lg bg-panel px-4 py-2 text-sm font-medium text-ink shadow focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 ${focusRing}`}
      >
        Skip to content
      </a>

      <header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link href="/prompts" className={`rounded-lg ${focusRing}`} aria-label="PromptDNA home">
            <Wordmark />
          </Link>

          <nav aria-label="Primary" className="flex items-center gap-1">
            {NAV.map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-lg px-2.5 py-1.5 text-sm transition ${focusRing} ${
                    active
                      ? "bg-accent-soft font-medium text-accent-ink"
                      : "text-ink-muted hover:bg-panel-muted hover:text-ink"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            {user && (
              <span className="hidden items-center gap-2 sm:flex" title={user.email}>
                <span
                  aria-hidden
                  className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-soft text-[11px] font-semibold text-accent-ink ring-1 ring-accent-line"
                >
                  {initials(user.name)}
                </span>
                <span className="max-w-[12ch] truncate text-sm text-ink-muted">{user.name}</span>
              </span>
            )}
            <button type="button" onClick={logout} className={buttonSecondary}>
              <LogOutIcon className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Log out</span>
              <span className="sr-only sm:hidden">Log out</span>
            </button>
          </div>
        </div>
      </header>

      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        {children}
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-xs text-ink-subtle sm:px-6">
          <span>PromptDNA — prompt lineage, experiments and retrieval.</span>
          <span className="flex items-center gap-1.5">
            <span>PostgreSQL</span>
            <span aria-hidden>·</span>
            <span>pgvector</span>
            <span aria-hidden>·</span>
            <span>Neo4j</span>
          </span>
        </div>
      </footer>
    </div>
  );
}
