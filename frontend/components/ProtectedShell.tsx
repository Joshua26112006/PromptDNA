"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/lib/auth-context";

import { AppShell } from "./AppShell";
import { Wordmark } from "./Wordmark";
import { Spinner } from "./ui";

/**
 * Gate for authenticated routes. While auth is resolving, shows a branded
 * placeholder (the protected UI is never briefly shown). If unauthenticated,
 * redirects to /login and renders nothing.
 */
export function ProtectedShell({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="flex min-h-full flex-1 flex-col items-center justify-center gap-5 p-8">
        <Wordmark size="lg" />
        <Spinner label="Checking your session…" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    return null;
  }

  return <AppShell>{children}</AppShell>;
}
