"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthLayout } from "@/components/AuthLayout";
import { buttonPrimary, ErrorBox, TextField, focusRing } from "@/components/ui";
import { ApiError, friendlyMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function RegisterPage() {
  const { register, status } = useAuth();
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/prompts");
  }, [status, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !email || !password) {
      setError("Fill in every field.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await register(name, email, password);
      router.replace("/prompts");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("An account with this email already exists.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError(friendlyMessage(err));
      } else if (err instanceof ApiError && err.status === 0) {
        setError("Unable to connect to the server.");
      } else {
        setError("Something went wrong. Please try again.");
      }
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={onSubmit} className="space-y-5" aria-labelledby="register-heading">
        <div>
          <h1 id="register-heading" className="text-2xl font-semibold tracking-tight text-ink">
            Create your account
          </h1>
          <p className="mt-1.5 text-sm text-ink-muted">
            Start building a versioned library of your prompts.
          </p>
        </div>

        <div className="space-y-4">
          <TextField
            label="Name"
            required
            maxLength={100}
            autoComplete="name"
            placeholder="Ada Lovelace"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <TextField
            label="Email"
            type="email"
            required
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            required
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            placeholder="••••••••"
            hint="At least 8 characters."
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && <ErrorBox message={error} />}

        <button type="submit" disabled={busy} className={`w-full ${buttonPrimary}`}>
          {busy ? "Creating…" : "Create account"}
        </button>

        <p className="text-sm text-ink-muted">
          Already have an account?{" "}
          <Link
            href="/login"
            className={`rounded font-medium text-accent underline underline-offset-2 ${focusRing}`}
          >
            Log in
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
