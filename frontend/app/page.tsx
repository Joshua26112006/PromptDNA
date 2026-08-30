"use client";

import Link from "next/link";

import { API_BASE_URL } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { user, loading, logout } = useAuth();

  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <div className="w-full max-w-xl space-y-4">
        <p className="text-sm font-mono uppercase tracking-widest text-neutral-500">
          Phase 3 · Authentication
        </p>
        <h1 className="text-3xl font-semibold">PromptDNA</h1>

        {loading ? (
          <p className="text-neutral-500">Checking session…</p>
        ) : user ? (
          <div className="space-y-3">
            <p className="text-neutral-700 dark:text-neutral-300">
              Signed in as <strong>{user.name}</strong> ({user.email}).
            </p>
            <dl className="rounded border border-neutral-200 p-3 text-sm dark:border-neutral-800">
              <div className="flex justify-between gap-4">
                <dt className="text-neutral-500">user_id</dt>
                <dd className="font-mono">{user.user_id}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-neutral-500">member since</dt>
                <dd className="font-mono">
                  {new Date(user.created_at).toLocaleString()}
                </dd>
              </div>
            </dl>
            <button
              onClick={logout}
              className="rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700"
            >
              Log out
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-neutral-600 dark:text-neutral-400">
              You are not signed in.
            </p>
            <div className="flex gap-3">
              <Link
                href="/login"
                className="rounded bg-neutral-900 px-3 py-1.5 text-sm text-white dark:bg-white dark:text-neutral-900"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700"
              >
                Register
              </Link>
            </div>
          </div>
        )}

        <p className="text-xs text-neutral-500">
          API: <code className="font-mono">{API_BASE_URL}</code> · only the
          authentication flow is built in this phase.
        </p>
      </div>
    </main>
  );
}
