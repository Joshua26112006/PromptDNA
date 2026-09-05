"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { buttonPrimary, card, ErrorBox, TextField } from "@/components/ui";
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
    <main className="relative flex flex-1 items-center justify-center overflow-hidden p-8">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,#e0e7ff,transparent_45%),radial-gradient(circle_at_80%_0%,#eef2ff,transparent_40%)] dark:bg-[radial-gradient(circle_at_20%_20%,rgba(30,27,75,0.4),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(49,46,129,0.25),transparent_40%)]"
      />
      <form
        onSubmit={onSubmit}
        className={`w-full max-w-sm space-y-4 p-7 ${card}`}
        aria-labelledby="register-heading"
      >
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white shadow-sm"
          >
            P
          </span>
          <h1 id="register-heading" className="text-xl font-semibold">
            Create your account
          </h1>
        </div>

        <TextField
          label="Name"
          required
          maxLength={100}
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <TextField
          label="Email"
          type="email"
          required
          autoComplete="email"
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
          hint="At least 8 characters."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <ErrorBox message={error} />}

        <button type="submit" disabled={busy} className={`w-full ${buttonPrimary}`}>
          {busy ? "Creating…" : "Create account"}
        </button>

        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Already have an account?{" "}
          <Link href="/login" className="underline">
            Log in
          </Link>
        </p>
      </form>
    </main>
  );
}
