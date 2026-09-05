"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { friendlyMessage, getPromptGraph } from "@/lib/api";
import type { GraphRelationship, GraphResponse } from "@/lib/types";

import { GitBranchIcon } from "./icons";
import { card, Spinner } from "./ui";

const ARROW: Record<string, string> = {
  DERIVED_FROM: "derived from",
  FORKED_FROM: "forked from",
  DEPENDS_ON: "depends on",
};

function RelRow({ r }: { r: GraphRelationship }) {
  const label =
    r.type && r.direction
      ? r.direction === "outgoing"
        ? `this prompt ${ARROW[r.type] ?? r.type} →`
        : `← ${ARROW[r.type] ?? r.type} this prompt`
      : (r.rel_types ?? []).join(" → ") || "connected";
  return (
    <li className="flex flex-wrap items-center gap-2 py-1.5 text-sm">
      <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:border-indigo-800/60 dark:bg-indigo-950/40 dark:text-indigo-300">
        {label}
      </span>
      <Link
        href={`/prompts/${r.prompt_id}`}
        className="font-medium text-neutral-800 underline decoration-neutral-300 underline-offset-2 hover:text-indigo-600 hover:decoration-indigo-400 dark:text-neutral-200 dark:hover:text-indigo-400"
      >
        {r.title}
      </Link>
      {r.depth > 1 && (
        <span className="text-xs text-neutral-500 dark:text-neutral-400">(depth {r.depth})</span>
      )}
    </li>
  );
}

/**
 * "Prompt Relationships (Knowledge Graph)" — Neo4j graph projection.
 *
 * Neo4j answers "how are these prompts explicitly connected?"
 * (derived / forked / depends-on) — distinct from semantic search, which finds
 * prompts with **similar meaning**. If the graph is unavailable, this section
 * degrades to a short message and never breaks the page.
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
      } catch (err) {
        if (!cancelled) {
          // 503 (Neo4j not enabled / unreachable) or any other error → soft fail
          void friendlyMessage(err);
          setState("unavailable");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [promptId]);

  return (
    <section aria-label="Prompt Relationships" className={`space-y-3 p-4 ${card}`}>
      <h2 className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        <GitBranchIcon className="h-4 w-4 text-neutral-400" />
        Prompt Relationships (Knowledge Graph)
      </h2>
      <p className="text-xs text-neutral-500 dark:text-neutral-400">
        Explicit connections between prompts (derived / forked / depends‑on),
        traversed in Neo4j. This is different from semantic search, which finds
        prompts with <em>similar meaning</em>.
      </p>

      {state === "loading" && <Spinner label="Loading graph…" />}
      {state === "unavailable" && (
        <p className="rounded-lg border border-dashed border-neutral-300 p-3 text-sm text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
          Graph relationships unavailable.
        </p>
      )}

      {state === "ok" && (
        <div className="space-y-4">
          <div>
            <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Ancestry</p>
            {ancestors && ancestors.relationships.length > 0 ? (
              <ol className="mt-1 divide-y divide-neutral-100 dark:divide-neutral-800">
                {ancestors.relationships.map((r) => (
                  <RelRow key={`a-${r.prompt_id}`} r={r} />
                ))}
              </ol>
            ) : (
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                No ancestor prompts — this prompt is a root.
              </p>
            )}
          </div>

          <div>
            <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
              Directly connected
            </p>
            {related && related.relationships.length > 0 ? (
              <ul className="mt-1 divide-y divide-neutral-100 dark:divide-neutral-800">
                {related.relationships.map((r) => (
                  <RelRow key={`r-${r.prompt_id}-${r.type}`} r={r} />
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                No connected prompts in the graph.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
