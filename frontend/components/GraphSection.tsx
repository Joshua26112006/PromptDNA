"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getPromptGraph } from "@/lib/api";
import type { GraphRelationship, GraphResponse } from "@/lib/types";

import { BranchIcon } from "./icons";
import { EmptyState, focusRing, SectionCard, Skeleton } from "./ui";

const PHRASE: Record<string, string> = {
  DERIVED_FROM: "derived from",
  FORKED_FROM: "forked from",
  DEPENDS_ON: "depends on",
};

function phrase(type: string | null | undefined): string {
  return (type && PHRASE[type]) || "linked to";
}

function RelPill({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-accent-line bg-accent-soft px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-accent-ink">
      {children}
    </span>
  );
}

function PromptLink({ id, title }: { id: string; title: string }) {
  return (
    <Link
      href={`/prompts/${id}`}
      className={`rounded font-medium text-ink underline decoration-line-strong underline-offset-2 transition-colors hover:text-accent hover:decoration-accent ${focusRing}`}
    >
      {title}
    </Link>
  );
}

/** One hop, written as a sentence so the direction is unambiguous. */
function ConnectionRow({ r }: { r: GraphRelationship }) {
  const label = phrase(r.type ?? (r.rel_types ?? [])[0]);
  const outgoing = r.direction !== "incoming";
  return (
    <li className="flex flex-wrap items-center gap-x-2 gap-y-1 py-2 text-sm text-ink-muted">
      {outgoing ? (
        <>
          <span>This prompt</span>
          <RelPill>{label}</RelPill>
          <PromptLink id={r.prompt_id} title={r.title} />
        </>
      ) : (
        <>
          <PromptLink id={r.prompt_id} title={r.title} />
          <RelPill>{label}</RelPill>
          <span>this prompt</span>
        </>
      )}
    </li>
  );
}

/**
 * Prompt Relationships — the Neo4j projection.
 *
 * Deliberately framed against semantic search: this section only ever shows
 * links that were *recorded* between prompts (lineage, forks, dependencies),
 * never prompts that merely read similarly.
 */
export function GraphSection({ promptId }: { promptId: string }) {
  const [related, setRelated] = useState<GraphResponse | null>(null);
  const [ancestors, setAncestors] = useState<GraphResponse | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "unavailable">("loading");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [rel, anc] = await Promise.all([
          getPromptGraph(promptId, "related"),
          getPromptGraph(promptId, "ancestors"),
        ]);
        if (cancelled) return;
        setRelated(rel);
        setAncestors(anc);
        setState("ok");
      } catch {
        // 503 (graph disabled / unreachable) or any other failure: this section
        // degrades on its own and never takes the page down with it.
        if (!cancelled) setState("unavailable");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [promptId]);

  const lineage = [...(ancestors?.relationships ?? [])].sort((a, b) => b.depth - a.depth);
  // A parent shows up in both traversals; showing it twice reads as a bug, so
  // the lineage chain wins and "directly connected" lists only what it adds.
  const inLineage = new Set(lineage.map((r) => r.prompt_id));
  const connections = (related?.relationships ?? []).filter((r) => !inLineage.has(r.prompt_id));
  const isolated = state === "ok" && lineage.length === 0 && connections.length === 0;

  return (
    <SectionCard
      title="Prompt Relationships"
      ariaLabel="Prompt Relationships"
      icon={BranchIcon}
      description="Links that were explicitly recorded between prompts — derived from, forked from, depends on. This is different from semantic search, which finds prompts with similar meaning."
    >
      {state === "loading" && (
        <div className="space-y-2" role="status" aria-live="polite">
          <span className="sr-only">Loading graph…</span>
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-3 w-56" />
        </div>
      )}

      {state === "unavailable" && (
        <p className="rounded-lg border border-dashed border-line-strong px-3.5 py-3 text-sm text-ink-muted">
          <span className="font-medium text-ink">Graph relationships unavailable.</span>{" "}
          The knowledge graph isn&apos;t reachable right now. Everything else on this
          page — versions, experiments and search — is unaffected.
        </p>
      )}

      {isolated && (
        <EmptyState
          icon={BranchIcon}
          title="This prompt stands alone"
          description="No relationships have been recorded between this prompt and any other. Creating a prompt from an existing one links them here. Similar-sounding prompts won't appear — that's what Semantic Search is for."
          compact
        />
      )}

      {state === "ok" && !isolated && (
        <div className="space-y-5">
          {lineage.length > 0 && (
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wide text-ink-subtle">
                Lineage
              </p>
              <ol className="mt-2">
                {lineage.map((r) => (
                  <li key={`a-${r.prompt_id}`} className="relative pl-5">
                    <span
                      aria-hidden
                      className="absolute bottom-0 left-[3px] top-4 w-px bg-line-strong"
                    />
                    <span
                      aria-hidden
                      className="absolute left-0 top-2 h-[7px] w-[7px] rounded-full border border-accent bg-panel"
                    />
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 pb-3 text-sm">
                      <PromptLink id={r.prompt_id} title={r.title} />
                      <RelPill>{phrase((r.rel_types ?? [])[0])}</RelPill>
                      {r.depth > 1 && (
                        <span className="text-xs text-ink-subtle tnum">{r.depth} steps back</span>
                      )}
                    </div>
                  </li>
                ))}
                <li className="relative pl-5">
                  <span
                    aria-hidden
                    className="absolute left-0 top-2 h-[7px] w-[7px] rounded-full bg-accent"
                  />
                  <p className="text-sm font-medium text-ink">This prompt</p>
                </li>
              </ol>
            </div>
          )}

          {connections.length > 0 && (
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wide text-ink-subtle">
                Directly connected
              </p>
              <ul className="mt-1 divide-y divide-line">
                {connections.map((r) => (
                  <ConnectionRow key={`r-${r.prompt_id}-${r.type}`} r={r} />
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </SectionCard>
  );
}
