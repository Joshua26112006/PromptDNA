"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CreateVersionForm } from "@/components/CreateVersionForm";
import { EditMetadataForm } from "@/components/EditMetadataForm";
import { ExperimentSection } from "@/components/ExperimentSection";
import { GraphSection } from "@/components/GraphSection";
import { ArrowLeftIcon, BeakerIcon, BranchIcon, LayersIcon, UserIcon } from "@/components/icons";
import {
  buttonPrimary,
  buttonSecondary,
  card,
  EmptyState,
  ErrorBox,
  focusRing,
  formatDay,
  Skeleton,
  Stat,
} from "@/components/ui";
import { VersionPanel } from "@/components/VersionPanel";
import { VersionTimeline } from "@/components/VersionTimeline";
import { VisibilityBadge } from "@/components/VisibilityBadge";
import { ApiError, friendlyMessage, getPrompt, getVersions } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Prompt, Version } from "@/lib/types";

type Mode = "view" | "editMeta" | "newVersion";
type LoadStatus = "loading" | "ok" | "notfound" | "error";

function BackLink() {
  return (
    <Link
      href="/prompts"
      className={`inline-flex items-center gap-1.5 rounded text-sm text-ink-muted transition-colors hover:text-ink ${focusRing}`}
    >
      <ArrowLeftIcon className="h-3.5 w-3.5" />
      Back to Prompt Library
    </Link>
  );
}

/** Resolves the parent prompt's title, degrading quietly if it isn't visible. */
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
    <span className="inline-flex items-center gap-1.5 text-sm text-ink-muted">
      <BranchIcon className="h-3.5 w-3.5 text-ink-subtle" />
      <span>Derived from</span>
      {accessible === null && <span className="text-ink-subtle">…</span>}
      {accessible === false && <span>another prompt (not visible to you)</span>}
      {accessible === true && (
        <Link
          href={`/prompts/${parentId}`}
          className={`rounded font-medium text-ink underline decoration-line-strong underline-offset-2 hover:text-accent hover:decoration-accent ${focusRing}`}
        >
          {label}
        </Link>
      )}
    </span>
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
  const [experimentCount, setExperimentCount] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("loading");
      setError(null);
      try {
        const [p, v] = await Promise.all([getPrompt(promptId), getVersions(promptId)]);
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
    return (
      <div className="space-y-6" role="status" aria-live="polite">
        <span className="sr-only">Loading prompt…</span>
        <Skeleton className="h-4 w-40" />
        <div className={`space-y-4 p-5 ${card}`}>
          <Skeleton className="h-7 w-72" />
          <Skeleton className="h-4 w-full max-w-lg" />
          <Skeleton className="h-10 w-full" />
        </div>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,17rem)_minmax(0,1fr)]">
          <Skeleton className="h-56 w-full" />
          <Skeleton className="h-80 w-full" />
        </div>
      </div>
    );
  }

  if (status === "notfound") {
    return (
      <div className="space-y-5">
        <BackLink />
        <EmptyState
          icon={LayersIcon}
          title="Prompt not found"
          description="This prompt doesn't exist, or it's private and belongs to someone else. Private prompts are invisible to everyone but their owner."
          action={
            <Link href="/prompts" className={buttonSecondary}>
              Back to Prompt Library
            </Link>
          }
        />
      </div>
    );
  }

  if (status === "error" || !prompt) {
    return (
      <div className="space-y-4">
        <BackLink />
        <ErrorBox message={error ?? "Could not load this prompt."} />
        <button type="button" className={buttonSecondary} onClick={reload}>
          Try again
        </button>
      </div>
    );
  }

  const isOwner = !!user && user.user_id === prompt.user_id;
  const latestNumber = prompt.latest_version ? prompt.latest_version.version_number : null;
  const selected =
    versions.find((v) => v.version_id === selectedId) ??
    [...versions].sort((a, b) => b.version_number - a.version_number)[0] ??
    null;

  return (
    <div className="space-y-6">
      <BackLink />

      {/* ---- identity + primary actions ---- */}
      <header className={`p-5 ${card}`}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div className="min-w-0 sm:flex-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-semibold tracking-tight text-ink">{prompt.title}</h1>
              <VisibilityBadge isPublic={prompt.is_public} />
            </div>
            {prompt.description && (
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-muted">
                {prompt.description}
              </p>
            )}
            {prompt.purpose && (
              <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-muted">
                <span className="text-ink-subtle">Purpose: </span>
                {prompt.purpose}
              </p>
            )}
            {prompt.parent_prompt_id && (
              <div className="mt-3">
                <LineageLink parentId={prompt.parent_prompt_id} />
              </div>
            )}
          </div>

          {isOwner && mode === "view" && (
            <div className="flex shrink-0 flex-wrap gap-2">
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

        <div className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-4 sm:grid-cols-4">
          <Stat icon={LayersIcon} label="Versions" value={versions.length} />
          <Stat
            icon={BeakerIcon}
            label="Experiments"
            value={experimentCount === null ? "—" : experimentCount}
          />
          <Stat icon={UserIcon} label="Owner" value={isOwner ? "You" : prompt.owner.name} />
          <Stat label="Updated" value={formatDay(prompt.updated_at)} />
        </div>
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

      {!isOwner && (
        <p className="text-xs text-ink-subtle">
          You are viewing another user&apos;s prompt. Only the owner can edit metadata,
          add versions, or run experiments.
        </p>
      )}

      {/* ---- workspace: version navigation beside the selected version ---- */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,17rem)_minmax(0,1fr)] lg:items-start">
        <div className={`max-h-80 overflow-auto p-4 lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] ${card}`}>
          <VersionTimeline
            versions={versions}
            latestNumber={latestNumber}
            selectedId={selected?.version_id ?? null}
            onSelect={setSelectedId}
          />
        </div>

        <div className="min-w-0 space-y-6">
          {selected ? (
            <VersionPanel
              version={selected}
              isCurrent={selected.version_number === latestNumber}
              creatorIsViewer={!!user && selected.created_by === user.user_id}
            />
          ) : (
            <EmptyState
              icon={LayersIcon}
              title="This prompt has no versions"
              description="Prompt text lives in versions. Create one to give this prompt content."
              compact
            />
          )}

          <ExperimentSection
            promptId={prompt.prompt_id}
            isOwner={isOwner}
            currentVersionId={prompt.latest_version ? prompt.latest_version.version_id : null}
            currentVersionNumber={latestNumber}
            onCountChange={setExperimentCount}
          />

          <GraphSection promptId={prompt.prompt_id} />
        </div>
      </div>
    </div>
  );
}
