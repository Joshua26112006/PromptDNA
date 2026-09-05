"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { buttonPrimary, card, ErrorBox, InfoNote, TextField } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function LoginForm() {
  const { login, status } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const expired = params.get("expired") === "1";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/prompts");
  }, [status, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) {
      setError("Enter your email and password.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      router.replace("/prompts");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Invalid email or password.");
      } else if (err instanceof ApiError && err.status === 0) {
        setError("Unable to connect to the server.");
      } else {
        setError("Something went wrong. Please try again.");
      }
      setBusy(false);
    }
  }

  return (
    <main className="relative flex flex-1 items-center justify-center overflow-hidden p-8">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,#e0e7ff,transparent_45%),radial-gradient(circle_at_80%_0%,#eef2ff,transparent_40%)] dark:bg-[radial-gradient(circle_at_20%_20%,rgba(30,27,75,0.4),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(49,46,129,0.25),transparent_40%)]"
      />
      <form
        onSubmit={onSubmit}
        className={`w-full max-w-sm space-y-4 p-7 ${card}`}
        aria-labelledby="login-heading"
      >
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white shadow-sm"
          >
            P
          </span>
          <h1 id="login-heading" className="text-xl font-semibold">
            Log in to PromptDNA
          </h1>
        </div>

        {expired && <InfoNote>Your session has expired. Please log in again.</InfoNote>}

        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <ErrorBox message={error} />}

        <button type="submit" disabled={busy} className={`w-full ${buttonPrimary}`}>
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          No account?{" "}
          <Link href="/register" className="underline">
            Create an account
          </Link>
        </p>
      </form>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
