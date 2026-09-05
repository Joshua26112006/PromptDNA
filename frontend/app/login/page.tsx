"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AuthLayout } from "@/components/AuthLayout";
import { buttonPrimary, ErrorBox, InfoNote, TextField, focusRing } from "@/components/ui";
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
    <form onSubmit={onSubmit} className="space-y-5" aria-labelledby="login-heading">
      <div>
        <h1 id="login-heading" className="text-2xl font-semibold tracking-tight text-ink">
          Log in to PromptDNA
        </h1>
        <p className="mt-1.5 text-sm text-ink-muted">
          Pick up where you left off with your prompt library.
        </p>
      </div>

      {expired && <InfoNote>Your session has expired. Please log in again.</InfoNote>}

      <div className="space-y-4">
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>

      {error && <ErrorBox message={error} />}

      <button type="submit" disabled={busy} className={`w-full ${buttonPrimary}`}>
        {busy ? "Signing in…" : "Sign in"}
      </button>

      <p className="text-sm text-ink-muted">
        No account?{" "}
        <Link
          href="/register"
          className={`rounded font-medium text-accent underline underline-offset-2 ${focusRing}`}
        >
          Create an account
        </Link>
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <AuthLayout>
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
