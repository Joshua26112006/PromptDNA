"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { friendlyMessage, getPromptGraph } from "@/lib/api";
import type { GraphRelationship, GraphResponse } from "@/lib/types";

import { Spinner } from "./ui";

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
    <li className="flex flex-wrap items-center gap-2 py-1 text-sm">
      <span className="rounded border border-neutral-300 px-1.5 py-0.5 text-[11px] font-semibold text-neutral-600 dark:border-neutral-700 dark:text-neutral-300">
        {label}
      </span>
      <Link href={`/prompts/${r.prompt_id}`} className="underline">
        {r.title}
      </Link>
      {r.depth > 1 && (
        <span className="text-xs text-neutral-500">(depth {r.depth})</span>
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
    <section aria-label="Prompt Relationships" className="space-y-2">
      <h2 className="text-sm font-semibold">Prompt Relationships (Knowledge Graph)</h2>
      <p className="text-xs text-neutral-500">
        Explicit connections between prompts (derived / forked / depends‑on),
        traversed in Neo4j. This is different from semantic search, which finds
        prompts with <em>similar meaning</em>.
      </p>

      {state === "loading" && <Spinner label="Loading graph…" />}
      {state === "unavailable" && (
        <p className="rounded border border-dashed border-neutral-300 p-3 text-sm text-neutral-500 dark:border-neutral-700">
          Graph relationships unavailable.
        </p>
      )}

      {state === "ok" && (
        <div className="space-y-3">
          <div>
            <p className="text-xs font-medium text-neutral-500">Ancestry</p>
            {ancestors && ancestors.relationships.length > 0 ? (
              <ol className="divide-y divide-neutral-200 dark:divide-neutral-800">
                {ancestors.relationships.map((r) => (
                  <RelRow key={`a-${r.prompt_id}`} r={r} />
                ))}
              </ol>
            ) : (
              <p className="text-sm text-neutral-500">
                No ancestor prompts — this prompt is a root.
              </p>
            )}
          </div>

          <div>
            <p className="text-xs font-medium text-neutral-500">
              Directly connected
            </p>
            {related && related.relationships.length > 0 ? (
              <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
                {related.relationships.map((r) => (
                  <RelRow key={`r-${r.prompt_id}-${r.type}`} r={r} />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-neutral-500">
                No connected prompts in the graph.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
