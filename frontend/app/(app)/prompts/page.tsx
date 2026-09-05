"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pagination } from "@/components/Pagination";
import { PromptCard } from "@/components/PromptCard";
import { VisibilityBadge } from "@/components/VisibilityBadge";
import { InboxIcon, PlusIcon, SearchIcon, SparklesIcon } from "@/components/icons";
import { buttonPrimary, card, cardInteractive, ErrorBox, fieldClass, Spinner } from "@/components/ui";
import { friendlyMessage, listPrompts, semanticSearch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { PromptListResponse, SemanticSearchResult } from "@/lib/types";

const LIMIT = 20;
type Visibility = "all" | "public" | "private";
type Mode = "lexical" | "semantic";

export default function PromptLibraryPage() {
  const { user } = useAuth();

  const [mode, setMode] = useState<Mode>("lexical");
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
      const isPublic =
        visibility === "all" ? undefined : visibility === "public";
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
    // semantic
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

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
    setSemantic(null);
    setOffset(0);
    if (next === "lexical") setLoading(true);
    else setLoading(false);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-50">
          Prompt Library
        </h1>
        <Link href="/prompts/new" className={buttonPrimary}>
          <PlusIcon className="h-4 w-4" />
          New Prompt
        </Link>
      </div>

      <div className={`space-y-4 p-4 ${card}`}>
        {/* search mode */}
        <fieldset className="flex items-center gap-1 rounded-lg border border-neutral-200 bg-neutral-50 p-1 text-sm dark:border-neutral-800 dark:bg-neutral-950/60">
          <legend className="sr-only">Search mode</legend>
          <label
            className={`flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-md px-3 py-1.5 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-indigo-500 ${
              mode === "lexical"
                ? "bg-white font-medium text-indigo-700 shadow-sm dark:bg-neutral-800 dark:text-indigo-300"
                : "text-neutral-500 hover:text-neutral-800 dark:text-neutral-400 dark:hover:text-neutral-200"
            }`}
          >
            <input
              type="radio"
              name="search-mode"
              checked={mode === "lexical"}
              onChange={() => switchMode("lexical")}
              className="sr-only"
            />
            <SearchIcon className="h-3.5 w-3.5" />
            Search by text
          </label>
          <label
            className={`flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-md px-3 py-1.5 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-indigo-500 ${
              mode === "semantic"
                ? "bg-white font-medium text-indigo-700 shadow-sm dark:bg-neutral-800 dark:text-indigo-300"
                : "text-neutral-500 hover:text-neutral-800 dark:text-neutral-400 dark:hover:text-neutral-200"
            }`}
          >
            <input
              type="radio"
              name="search-mode"
              checked={mode === "semantic"}
              onChange={() => switchMode("semantic")}
              className="sr-only"
            />
            <SparklesIcon className="h-3.5 w-3.5" />
            Semantic Search
          </label>
        </fieldset>

        <div className="flex flex-wrap items-end gap-3">
          <form onSubmit={onSearchSubmit} role="search" className="flex flex-1 items-end gap-2">
            <div className="min-w-[16rem] flex-1 space-y-1.5">
              <label htmlFor="prompt-search" className="block text-sm font-medium text-neutral-800 dark:text-neutral-200">
                {mode === "lexical" ? "Search" : "Describe what you're looking for"}
              </label>
              <div className="relative">
                <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <input
                  id="prompt-search"
                  type="search"
                  placeholder={
                    mode === "lexical"
                      ? "Search by title…"
                      : "Prompts for summarizing academic papers"
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
            <div className="space-y-1.5">
              <label htmlFor="visibility-filter" className="block text-sm font-medium text-neutral-800 dark:text-neutral-200">
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

        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          {mode === "lexical" ? (
            <>
              Text search is a lexical title match (PostgreSQL <code>ILIKE</code>).
            </>
          ) : (
            <>
              Semantic search finds prompts with similar meaning, even when the
              wording is different. It searches your prompts and public prompts.
            </>
          )}
        </p>
      </div>

      {loading && (
        <Spinner
          label={mode === "lexical" ? "Loading prompts…" : "Searching…"}
        />
      )}
      {error && !loading && <ErrorBox message={error} />}

      {/* lexical results */}
      {mode === "lexical" && !loading && !error && data && (
        <>
          {data.items.length === 0 ? (
            <p className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-neutral-300 p-8 text-center text-sm text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
              <InboxIcon className="h-6 w-6 text-neutral-400" />
              No prompts found.{" "}
              <Link href="/prompts/new" className="font-medium text-indigo-600 underline dark:text-indigo-400">
                Create one
              </Link>
              .
            </p>
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2">
              {data.items.map((p) => (
                <PromptCard
                  key={p.prompt_id}
                  prompt={p}
                  ownedByViewer={p.user_id === user?.user_id}
                />
              ))}
            </ul>
          )}
          <Pagination
            offset={data.offset}
            limit={data.limit}
            total={data.total}
            onChange={setOffset}
          />
        </>
      )}

      {/* semantic results */}
      {mode === "semantic" && !loading && !error && semantic !== null && (
        <section aria-label="Semantic search results" className="space-y-2">
          <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
            Semantic search results ({semantic.length})
          </h2>
          {semantic.length === 0 ? (
            <p className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-neutral-300 p-8 text-center text-sm text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
              <SparklesIcon className="h-6 w-6 text-neutral-400" />
              No semantically similar prompts found. Some versions may not have
              embeddings yet.
            </p>
          ) : (
            <ul className="space-y-2">
              {semantic.map((r) => (
                <li key={r.version_id}>
                  <Link
                    href={`/prompts/${r.prompt_id}`}
                    className={`block p-3.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${cardInteractive}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="flex items-center gap-2">
                        <span className="font-medium">{r.prompt_title}</span>
                        <span className="font-mono text-xs text-neutral-500 dark:text-neutral-400">
                          Version {r.version_number}
                        </span>
                        <VisibilityBadge isPublic={r.is_public} />
                      </span>
                      <span className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:border-indigo-800/60 dark:bg-indigo-950/40 dark:text-indigo-300">
                        <SparklesIcon className="h-3 w-3" />
                        similarity {r.similarity.toFixed(3)}
                      </span>
                    </div>
                    <p className="mt-1.5 line-clamp-2 font-mono text-xs text-neutral-600 dark:text-neutral-400">
                      {r.content_preview}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
