"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pagination } from "@/components/Pagination";
import { PromptCard } from "@/components/PromptCard";
import { buttonPrimary, ErrorBox, Spinner } from "@/components/ui";
import { friendlyMessage, listPrompts } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { PromptListResponse } from "@/lib/types";

const LIMIT = 20;
type Visibility = "all" | "public" | "private";

export default function PromptLibraryPage() {
  const { user } = useAuth();

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [visibility, setVisibility] = useState<Visibility>("all");
  const [offset, setOffset] = useState(0);

  const [data, setData] = useState<PromptListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
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
  }, [offset, search, visibility]);

  function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setOffset(0);
    setSearch(searchInput.trim());
  }

  function onVisibilityChange(next: Visibility) {
    setOffset(0);
    setVisibility(next);
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Prompt Library</h1>
        <Link href="/prompts/new" className={buttonPrimary}>
          + New Prompt
        </Link>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <form onSubmit={onSearchSubmit} role="search" className="flex items-end gap-2">
          <div className="space-y-1">
            <label htmlFor="prompt-search" className="block text-sm font-medium">
              Search
            </label>
            <input
              id="prompt-search"
              type="search"
              placeholder="Search by title…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-64 rounded border border-neutral-300 bg-transparent px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500 dark:border-neutral-700"
            />
          </div>
          <button type="submit" className="rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700">
            Search
          </button>
        </form>

        <div className="space-y-1">
          <label htmlFor="visibility-filter" className="block text-sm font-medium">
            Visibility
          </label>
          <select
            id="visibility-filter"
            value={visibility}
            onChange={(e) => onVisibilityChange(e.target.value as Visibility)}
            className="rounded border border-neutral-300 bg-transparent px-3 py-2 text-sm dark:border-neutral-700"
          >
            <option value="all">All</option>
            <option value="public">Public</option>
            <option value="private">Private</option>
          </select>
        </div>
      </div>

      <p className="text-xs text-neutral-500">
        Search is a lexical title match (PostgreSQL <code>ILIKE</code>). Semantic
        search is not implemented yet.
      </p>

      {loading && <Spinner label="Loading prompts…" />}
      {error && !loading && <ErrorBox message={error} />}

      {!loading && !error && data && (
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
    </div>
  );
}
