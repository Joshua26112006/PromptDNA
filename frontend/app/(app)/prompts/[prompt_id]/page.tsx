"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CreateVersionForm } from "@/components/CreateVersionForm";
import { EditMetadataForm } from "@/components/EditMetadataForm";
import { buttonPrimary, buttonSecondary, ErrorBox, formatDate, Spinner } from "@/components/ui";
import { VersionHistory } from "@/components/VersionHistory";
import { VersionPanel } from "@/components/VersionPanel";
import { VisibilityBadge } from "@/components/VisibilityBadge";
import { ApiError, friendlyMessage, getPrompt, getVersions } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Prompt, Version } from "@/lib/types";

type Mode = "view" | "editMeta" | "newVersion";
type LoadStatus = "loading" | "ok" | "notfound" | "error";

function LineageLink({ parentId }: { parentId: string }) {
  const [label, setLabel] = useState<string | null>(null);
  const [accessible, setAccessible] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    getPrompt(parentId)
      .then((p) => {
        if (!cancelled) {
          setLabel(p.title);
          setAccessible(true);
        }
      })
      .catch(() => {
        if (!cancelled) setAccessible(false);
      });
    return () => {
      cancelled = true;
    };
  }, [parentId]);

  return (
    <p className="text-sm">
      <span className="text-neutral-500">Derived from: </span>
      {accessible === null && <span className="text-neutral-400">loading…</span>}
      {accessible === false && (
        <span className="text-neutral-500">another prompt (not accessible to you)</span>
      )}
      {accessible === true && (
        <Link href={`/prompts/${parentId}`} className="underline">
          {label}
        </Link>
      )}
    </p>
  );
}

export default function PromptDetailPage() {
  const params = useParams<{ prompt_id: string }>();
  const promptId = params.prompt_id;
  const { user, logout } = useAuth();

  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("view");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("loading");
      setError(null);
      try {
        const [p, v] = await Promise.all([
          getPrompt(promptId),
          getVersions(promptId),
        ]);
        if (cancelled) return;
        setPrompt(p);
        setVersions(v.items);
        setStatus("ok");
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setStatus("notfound");
        } else if (err instanceof ApiError && err.status === 401) {
          logout();
        } else {
          setStatus("error");
          setError(friendlyMessage(err));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [promptId, reloadKey, logout]);

  const reload = () => setReloadKey((k) => k + 1);

  if (status === "loading") {
    return <Spinner label="Loading prompt…" />;
  }

  if (status === "notfound") {
    return (
      <div className="space-y-3">
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Prompt not found. It may be private, or it may not exist.
        </p>
        <Link href="/prompts" className={buttonSecondary}>
          ← Back to Prompt Library
        </Link>
      </div>
    );
  }

  if (status === "error" || !prompt) {
    return (
      <div className="space-y-3">
        <ErrorBox message={error ?? "Could not load this prompt."} />
        <button type="button" className={buttonSecondary} onClick={reload}>
          Retry
        </button>
      </div>
    );
  }

  const isOwner = !!user && user.user_id === prompt.user_id;
  const latestNumber = prompt.latest_version
    ? prompt.latest_version.version_number
    : null;
  const selected =
    versions.find((v) => v.version_id === selectedId) ??
    [...versions].sort((a, b) => b.version_number - a.version_number)[0] ??
    null;

  return (
    <div className="space-y-6">
      <Link href="/prompts" className="text-sm text-neutral-500 hover:underline">
        ← Back to Prompt Library
      </Link>

      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold">{prompt.title}</h1>
            <VisibilityBadge isPublic={prompt.is_public} />
          </div>
          {isOwner && mode === "view" && (
            <div className="flex gap-2">
              <button
                type="button"
                className={buttonSecondary}
                onClick={() => setMode("editMeta")}
              >
                Edit Metadata
              </button>
              <button
                type="button"
                className={buttonPrimary}
                onClick={() => setMode("newVersion")}
              >
                Create New Version
              </button>
            </div>
          )}
        </div>

        {prompt.description && (
          <p className="text-sm text-neutral-700 dark:text-neutral-300">
            {prompt.description}
          </p>
        )}

        <dl className="grid grid-cols-1 gap-1 text-xs text-neutral-500 sm:grid-cols-2">
          <div>
            <dt className="inline font-medium">Purpose: </dt>
            <dd className="inline">{prompt.purpose ?? "—"}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Owner: </dt>
            <dd className="inline">{isOwner ? "you" : prompt.owner.name}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Created: </dt>
            <dd className="inline">{formatDate(prompt.created_at)}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Updated: </dt>
            <dd className="inline">{formatDate(prompt.updated_at)}</dd>
          </div>
        </dl>

        {prompt.parent_prompt_id && <LineageLink parentId={prompt.parent_prompt_id} />}
      </header>

      {isOwner && mode === "editMeta" && (
        <EditMetadataForm
          prompt={prompt}
          onCancel={() => setMode("view")}
          onSaved={(updated) => {
            setPrompt(updated);
            setMode("view");
          }}
        />
      )}
      {isOwner && mode === "newVersion" && (
        <CreateVersionForm
          promptId={prompt.prompt_id}
          onCancel={() => setMode("view")}
          onCreated={(version) => {
            setMode("view");
            setSelectedId(version.version_id);
            reload();
          }}
        />
      )}

      {selected ? (
        <VersionPanel
          version={selected}
          isCurrent={selected.version_number === latestNumber}
          creatorIsViewer={!!user && selected.created_by === user.user_id}
        />
      ) : (
        <p className="text-sm text-neutral-500">This prompt has no versions.</p>
      )}

      <VersionHistory
        versions={versions}
        latestNumber={latestNumber}
        selectedId={selected?.version_id ?? null}
        onSelect={setSelectedId}
      />

      {!isOwner && (
        <p className="text-xs text-neutral-500">
          You are viewing another user&apos;s prompt. Only the owner can edit
          metadata or add versions.
        </p>
      )}
    </div>
  );
}
