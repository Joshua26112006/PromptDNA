"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pagination } from "@/components/Pagination";
import { PromptCard } from "@/components/PromptCard";
import { VisibilityBadge } from "@/components/VisibilityBadge";
import { buttonPrimary, ErrorBox, Spinner } from "@/components/ui";
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
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Prompt Library</h1>
        <Link href="/prompts/new" className={buttonPrimary}>
          + New Prompt
        </Link>
      </div>

      {/* search mode */}
      <fieldset className="flex items-center gap-4 text-sm">
        <legend className="sr-only">Search mode</legend>
        <label className="inline-flex items-center gap-2">
          <input
            type="radio"
            name="search-mode"
            checked={mode === "lexical"}
            onChange={() => switchMode("lexical")}
          />
          Search by text
        </label>
        <label className="inline-flex items-center gap-2">
          <input
            type="radio"
            name="search-mode"
            checked={mode === "semantic"}
            onChange={() => switchMode("semantic")}
          />
          Semantic Search
        </label>
      </fieldset>

      <div className="flex flex-wrap items-end gap-3">
        <form onSubmit={onSearchSubmit} role="search" className="flex items-end gap-2">
          <div className="space-y-1">
            <label htmlFor="prompt-search" className="block text-sm font-medium">
              {mode === "lexical" ? "Search" : "Describe what you're looking for"}
            </label>
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
              className="w-72 rounded border border-neutral-300 bg-transparent px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500 dark:border-neutral-700"
            />
          </div>
          <button
            type="submit"
            className="rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700"
          >
            {mode === "lexical" ? "Search" : "Search"}
          </button>
        </form>

        {mode === "lexical" && (
          <div className="space-y-1">
            <label htmlFor="visibility-filter" className="block text-sm font-medium">
              Visibility
            </label>
            <select
              id="visibility-filter"
              value={visibility}
              onChange={(e) => {
                setOffset(0);
                setVisibility(e.target.value as Visibility);
              }}
              className="rounded border border-neutral-300 bg-transparent px-3 py-2 text-sm dark:border-neutral-700"
            >
              <option value="all">All</option>
              <option value="public">Public</option>
              <option value="private">Private</option>
            </select>
          </div>
        )}
      </div>

      <p className="text-xs text-neutral-500">
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
            <p className="rounded border border-dashed border-neutral-300 p-6 text-center text-sm text-neutral-500 dark:border-neutral-700">
              No prompts found.{" "}
              <Link href="/prompts/new" className="underline">
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
          <h2 className="text-sm font-semibold">
            Semantic search results ({semantic.length})
          </h2>
          {semantic.length === 0 ? (
            <p className="rounded border border-dashed border-neutral-300 p-6 text-center text-sm text-neutral-500 dark:border-neutral-700">
              No semantically similar prompts found. Some versions may not have
              embeddings yet.
            </p>
          ) : (
            <ul className="space-y-2">
              {semantic.map((r) => (
                <li key={r.version_id}>
                  <Link
                    href={`/prompts/${r.prompt_id}`}
                    className="block rounded border border-neutral-200 p-3 hover:border-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-500 dark:border-neutral-800 dark:hover:border-neutral-600"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="flex items-center gap-2">
                        <span className="font-medium">{r.prompt_title}</span>
                        <span className="font-mono text-xs text-neutral-500">
                          Version {r.version_number}
                        </span>
                        <VisibilityBadge isPublic={r.is_public} />
                      </span>
                      <span className="text-xs text-neutral-500">
                        similarity {r.similarity.toFixed(3)}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 font-mono text-xs text-neutral-600 dark:text-neutral-400">
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
