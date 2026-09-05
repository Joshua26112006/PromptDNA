"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pagination } from "@/components/Pagination";
import { PromptCard } from "@/components/PromptCard";
import { SearchModeToggle, type SearchMode } from "@/components/SearchModeToggle";
import { VisibilityBadge } from "@/components/VisibilityBadge";
import { FileTextIcon, PlusIcon, SearchIcon, SparklesIcon } from "@/components/icons";
import {
  buttonPrimary,
  card,
  cardInteractive,
  EmptyState,
  ErrorBox,
  fieldClass,
  focusRing,
  PageHeader,
  Skeleton,
  Spinner,
  well,
} from "@/components/ui";
import { friendlyMessage, listPrompts, semanticSearch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { PromptListResponse, SemanticSearchResult } from "@/lib/types";

const LIMIT = 20;
type Visibility = "all" | "public" | "private";

export default function PromptLibraryPage() {
  const { user } = useAuth();

  const [mode, setMode] = useState<SearchMode>("lexical");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [visibility, setVisibility] = useState<Visibility>("all");
  const [offset, setOffset] = useState(0);

  const [data, setData] = useState<PromptListResponse | null>(null);
  const [semantic, setSemantic] = useState<SemanticSearchResult[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Lexical listing (also the default view).
  useEffect(() => {
    if (mode !== "lexical") return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      const isPublic = visibility === "all" ? undefined : visibility === "public";
      try {
        const res = await listPrompts({
          limit: LIMIT,
          offset,
          search: search || undefined,
          isPublic,
        });
        if (!cancelled) setData(res);
      } catch (err) {
        if (!cancelled) setError(friendlyMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mode, offset, search, visibility]);

  async function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = searchInput.trim();
    if (mode === "lexical") {
      setOffset(0);
      setSearch(q);
      return;
    }
    if (!q) return;
    setLoading(true);
    setError(null);
    setSemantic(null);
    try {
      const res = await semanticSearch(q, { limit: 15 });
      setSemantic(res.results);
    } catch (err) {
      setError(friendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function switchMode(next: SearchMode) {
    setMode(next);
    setError(null);
    setSemantic(null);
    setOffset(0);
    setLoading(next === "lexical");
  }

  const filtered = search !== "" || visibility !== "all";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Prompt Library"
        description="Every prompt you own, plus the public prompts shared by others. Open one to see its versions, experiments and relationships."
        actions={
          <Link href="/prompts/new" className={buttonPrimary}>
            <PlusIcon className="h-4 w-4" />
            New Prompt
          </Link>
        }
      />

      {/* ---- retrieval controls ---- */}
      <div className={`space-y-4 p-4 sm:p-5 ${card}`}>
        <SearchModeToggle mode={mode} onChange={switchMode} />

        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <form onSubmit={onSearchSubmit} role="search" className="flex flex-1 items-end gap-2">
            <div className="min-w-0 flex-1 space-y-1.5">
              <label htmlFor="prompt-search" className="block text-sm font-medium text-ink">
                {mode === "lexical" ? "Search" : "Describe what you're looking for"}
              </label>
              <div className="relative">
                <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
                <input
                  id="prompt-search"
                  type="search"
                  placeholder={
                    mode === "lexical"
                      ? "Search by title…"
                      : "e.g. prompts that summarise academic papers"
                  }
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className={`${fieldClass} pl-9`}
                />
              </div>
            </div>
            <button type="submit" className={buttonPrimary}>
              Search
            </button>
          </form>

          {mode === "lexical" && (
            <div className="space-y-1.5 sm:w-44">
              <label htmlFor="visibility-filter" className="block text-sm font-medium text-ink">
                Visibility
              </label>
              <select
                id="visibility-filter"
                value={visibility}
                onChange={(e) => {
                  setOffset(0);
                  setVisibility(e.target.value as Visibility);
                }}
                className={fieldClass}
              >
                <option value="all">All</option>
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {error && !loading && <ErrorBox message={error} />}

      {/* ---- lexical results ---- */}
      {mode === "lexical" && (
        <>
          {loading ? (
            <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <li key={i} className={`space-y-3 p-4 ${card}`}>
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-4/5" />
                  <Skeleton className="h-3 w-1/3" />
                </li>
              ))}
            </ul>
          ) : !error && data ? (
            data.items.length === 0 ? (
              filtered ? (
                <EmptyState
                  icon={SearchIcon}
                  title="No prompts match this search"
                  description="Try a shorter or more general term, clear the visibility filter, or switch to Semantic Search to match on meaning instead of exact words."
                />
              ) : (
                <EmptyState
                  icon={FileTextIcon}
                  title="Your library is empty"
                  description="A prompt is a reusable instruction for a model. PromptDNA keeps every edit as its own immutable version, so you can compare them and test them against models over time."
                  action={
                    <Link href="/prompts/new" className={buttonPrimary}>
                      <PlusIcon className="h-4 w-4" />
                      Create your first prompt
                    </Link>
                  }
                />
              )
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-ink-muted tnum">
                  {data.total} {data.total === 1 ? "prompt" : "prompts"}
                  {search && <> matching “{search}”</>}
                </p>
                <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {data.items.map((p) => (
                    <PromptCard
                      key={p.prompt_id}
                      prompt={p}
                      ownedByViewer={p.user_id === user?.user_id}
                    />
                  ))}
                </ul>
                <Pagination
                  offset={data.offset}
                  limit={data.limit}
                  total={data.total}
                  onChange={setOffset}
                />
              </div>
            )
          ) : null}
        </>
      )}

      {/* ---- semantic results ---- */}
      {mode === "semantic" && (
        <>
          {loading && <Spinner label="Searching…" />}

          {!loading && !error && semantic === null && (
            <EmptyState
              icon={SparklesIcon}
              title="Search by meaning"
              description="Describe the job you want a prompt to do. PromptDNA compares the meaning of your description against every prompt version you can see — so “condense a paper” can find a prompt that says “summarise research”."
            />
          )}

          {!loading && !error && semantic !== null && (
            <section aria-label="Semantic search results" className="space-y-3">
              <h2 className="text-sm font-semibold text-ink">
                Semantic search results ({semantic.length})
              </h2>

              {semantic.length === 0 ? (
                <EmptyState
                  icon={SparklesIcon}
                  title="No semantically similar prompts found"
                  description="Nothing you can access is close in meaning to that description. Try describing the task differently — or note that versions without a generated embedding are not searchable this way."
                  compact
                />
              ) : (
                <ul className="space-y-2">
                  {semantic.map((r) => (
                    <li key={r.version_id}>
                      <Link
                        href={`/prompts/${r.prompt_id}`}
                        className={`group block p-4 ${cardInteractive} ${focusRing}`}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
                          <div className="flex min-w-0 flex-wrap items-center gap-2">
                            <span className="font-medium text-ink transition-colors group-hover:text-accent">
                              {r.prompt_title}
                            </span>
                            <span className="font-mono text-xs text-ink-subtle tnum">
                              v{r.version_number}
                            </span>
                            <VisibilityBadge isPublic={r.is_public} />
                          </div>
                          <SimilarityMeter value={r.similarity} />
                        </div>
                        <p className={`mt-2.5 line-clamp-2 p-2.5 font-mono text-xs leading-relaxed text-ink-muted ${well}`}>
                          {r.content_preview}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

/** Similarity as a bar + its exact value (cosine similarity, 0–1). */
function SimilarityMeter({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <span className="flex shrink-0 items-center gap-2">
      <span aria-hidden className="h-1.5 w-16 overflow-hidden rounded-full bg-line">
        <span className="block h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
      </span>
      <span className="font-mono text-xs text-ink-muted tnum">
        similarity {value.toFixed(3)}
      </span>
    </span>
  );
}
