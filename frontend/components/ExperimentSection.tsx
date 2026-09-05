"use client";

import { useEffect, useState } from "react";

import { friendlyMessage, listPromptExperiments } from "@/lib/api";
import type { Experiment } from "@/lib/types";

import { ExperimentStatusBadge } from "./ExperimentStatusBadge";
import { BeakerIcon } from "./icons";
import { RunExperimentForm } from "./RunExperimentForm";
import {
  buttonPrimary,
  Chip,
  EmptyState,
  ErrorBox,
  formatDate,
  SectionCard,
  Skeleton,
  well,
} from "./ui";

function scoreLabel(score: Experiment["score"]): string {
  if (score === null || score === undefined) return "Not scored";
  return `${Number(score)}/10`;
}

function ExperimentRow({ e }: { e: Experiment }) {
  return (
    <li className="py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <ExperimentStatusBadge status={e.status} />
          <span className="text-sm font-medium text-ink">{e.model_name}</span>
          <Chip>{e.provider}</Chip>
        </div>
        <Chip mono>v{e.version_number}</Chip>
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-xs">
        <div>
          <dt className="text-[11px] uppercase tracking-wide text-ink-subtle">Response time</dt>
          <dd className="mt-0.5 font-mono text-sm text-ink tnum">
            {e.response_time_ms === null ? "—" : `${(e.response_time_ms / 1000).toFixed(2)}s`}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-wide text-ink-subtle">Score</dt>
          <dd className="mt-0.5 text-sm text-ink tnum">{scoreLabel(e.score)}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-wide text-ink-subtle">Executed</dt>
          <dd className="mt-0.5 text-sm text-ink">{formatDate(e.executed_at)}</dd>
        </div>
      </dl>

      {e.status === "FAILED" && e.error_message && (
        <p className="mt-3 rounded-lg border border-danger-line bg-danger-soft px-3 py-2 text-xs leading-relaxed text-danger">
          {e.error_message}
        </p>
      )}

      {e.status === "SUCCESS" && e.output && (
        <div className="mt-3">
          <p className="mb-1.5 text-[11px] uppercase tracking-wide text-ink-subtle">Model output</p>
          <pre className={`max-h-64 overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-xs leading-relaxed text-ink ${well}`}>{e.output}</pre>
        </div>
      )}

      {e.notes && (
        <p className="mt-3 text-xs text-ink-muted">
          <span className="text-ink-subtle">Notes: </span>
          {e.notes}
        </p>
      )}
    </li>
  );
}

/**
 * Experiment history + (owner only) "Run Experiment" against the current
 * version. The backend enforces owner-only execution regardless of what the UI
 * chooses to show.
 */
export function ExperimentSection({
  promptId,
  isOwner,
  currentVersionId,
  currentVersionNumber,
  onCountChange,
}: {
  promptId: string;
  isOwner: boolean;
  currentVersionId: string | null;
  currentVersionNumber: number | null;
  /** reports the loaded experiment count so the page header can show it */
  onCountChange?: (count: number) => void;
}) {
  const [experiments, setExperiments] = useState<Experiment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await listPromptExperiments(promptId);
        if (!cancelled) {
          setExperiments(res.items);
          onCountChange?.(res.items.length);
        }
      } catch (err) {
        if (!cancelled) setError(friendlyMessage(err));
      }
    })();
    return () => {
      cancelled = true;
    };
    // `onCountChange` is a reporting callback; re-fetching when its identity
    // changes would loop against a parent that recreates it each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [promptId, reloadKey]);

  const canRun = isOwner && currentVersionId && currentVersionNumber !== null;

  return (
    <SectionCard
      title="Experiments"
      icon={BeakerIcon}
      description="An experiment sends one immutable version's exact text to a model and stores what came back — the output, how long it took, and whether it succeeded."
      actions={
        canRun && !showForm ? (
          <button type="button" className={buttonPrimary} onClick={() => setShowForm(true)}>
            Run Experiment
          </button>
        ) : undefined
      }
    >
      <div className="space-y-3">
        {canRun && showForm && (
          <RunExperimentForm
            promptId={promptId}
            versionId={currentVersionId}
            versionNumber={currentVersionNumber}
            onCancel={() => setShowForm(false)}
            onComplete={() => {
              setShowForm(false);
              setReloadKey((k) => k + 1);
            }}
          />
        )}

        {error && <ErrorBox message={error} />}

        {experiments === null && !error && (
          <div className="space-y-3 py-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-64" />
            <Skeleton className="h-3 w-52" />
          </div>
        )}

        {experiments !== null && experiments.length === 0 && (
          <EmptyState
            icon={BeakerIcon}
            title="No experiments yet"
            description={
              isOwner
                ? "Run this prompt against a model to record its output, response time and status. Results stay attached to the exact version they ran against, so you can compare versions fairly."
                : "The owner hasn't recorded any model runs for this prompt yet."
            }
            compact
          />
        )}

        {experiments !== null && experiments.length > 0 && (
          <ul className="divide-y divide-line">
            {experiments.map((e) => (
              <ExperimentRow key={e.experiment_id} e={e} />
            ))}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}
