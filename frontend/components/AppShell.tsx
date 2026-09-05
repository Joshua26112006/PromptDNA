"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/lib/auth-context";

import { LogOutIcon } from "./icons";
import { buttonSecondary } from "./ui";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const chars = parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "");
  return chars.join("") || "?";
}

/** Header + main region for authenticated pages. */
export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const onLibrary = pathname?.startsWith("/prompts");

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-10 border-b border-neutral-200 bg-white/80 backdrop-blur-sm dark:border-neutral-800 dark:bg-neutral-950/80">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-6">
            <Link href="/prompts" className="flex items-center gap-2">
              <span
                aria-hidden
                className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold text-white shadow-sm"
              >
                P
              </span>
              <span className="font-semibold tracking-tight">PromptDNA</span>
            </Link>
            <nav aria-label="Primary">
              <Link
                href="/prompts"
                aria-current={onLibrary ? "page" : undefined}
                className={
                  onLibrary
                    ? "text-sm font-medium text-indigo-600 dark:text-indigo-400"
                    : "text-sm text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100"
                }
              >
                Prompt Library
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {user && (
              <span className="hidden items-center gap-2 sm:flex" title={user.email}>
                <span
                  aria-hidden
                  className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-200 text-[10px] font-semibold text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
                >
                  {initials(user.name)}
                </span>
                <span className="text-neutral-500 dark:text-neutral-400">{user.name}</span>
              </span>
            )}
            <button type="button" onClick={logout} className={buttonSecondary}>
              <LogOutIcon className="h-3.5 w-3.5" />
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
    </div>
  );
}
