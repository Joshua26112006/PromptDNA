"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Wordmark } from "@/components/Wordmark";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";

/** Entry point: route to the Prompt Library or the login page. */
export default function Home() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") router.replace("/prompts");
    else if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-5 p-8">
      <Wordmark size="lg" />
      <Spinner label="Loading PromptDNA…" />
    </main>
  );
}
