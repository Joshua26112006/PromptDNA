"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/lib/auth-context";

import { AppShell } from "./AppShell";
import { Spinner } from "./ui";

/**
 * Gate for authenticated routes. While auth is resolving, shows a spinner (the
 * protected UI is never briefly shown). If unauthenticated, redirects to
 * /login and renders nothing.
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
      <div className="flex min-h-full items-center justify-center p-8">
        <Spinner label="Checking your session…" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    return null;
  }

  return <AppShell>{children}</AppShell>;
}
