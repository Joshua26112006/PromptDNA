"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useAuth } from "@/lib/auth-context";

import { buttonSecondary } from "./ui";

/** Header + main region for authenticated pages. */
export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-neutral-200 dark:border-neutral-800">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-6">
            <Link href="/prompts" className="font-semibold tracking-tight">
              PromptDNA
            </Link>
            <nav aria-label="Primary">
              <Link
                href="/prompts"
                className="text-sm text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100"
              >
                Prompt Library
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {user && (
              <span className="hidden text-neutral-500 sm:inline" title={user.email}>
                {user.name}
              </span>
            )}
            <button type="button" onClick={logout} className={buttonSecondary}>
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
