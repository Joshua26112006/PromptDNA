"use client";

import { useEffect, useState } from "react";

import { friendlyMessage, listPromptExperiments } from "@/lib/api";
import type { Experiment } from "@/lib/types";

import { ExperimentStatusBadge } from "./ExperimentStatusBadge";
import { RunExperimentForm } from "./RunExperimentForm";
import { buttonPrimary, ErrorBox, formatDate, Spinner } from "./ui";

function scoreLabel(score: Experiment["score"]): string {
  if (score === null || score === undefined) return "Not scored";
  return `${Number(score)}/10`;
}

function ExperimentRow({ e }: { e: Experiment }) {
  return (
    <li className="rounded border border-neutral-200 p-3 dark:border-neutral-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ExperimentStatusBadge status={e.status} />
          <span className="text-sm font-medium">{e.model_name}</span>
          <span className="text-xs text-neutral-500">({e.provider})</span>
        </div>
        <span className="font-mono text-xs text-neutral-500">
          Version {e.version_number}
        </span>
      </div>

      <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-500">
        <div>
          <dt className="inline">Response time: </dt>
          <dd className="inline">
            {e.response_time_ms === null
              ? "—"
              : `${(e.response_time_ms / 1000).toFixed(2)}s`}
          </dd>
        </div>
        <div>
          <dt className="inline">Score: </dt>
          <dd className="inline">{scoreLabel(e.score)}</dd>
        </div>
        <div>
          <dt className="inline">Executed: </dt>
          <dd className="inline">{formatDate(e.executed_at)}</dd>
        </div>
      </dl>

      {e.status === "FAILED" && e.error_message && (
        <p className="mt-2 text-xs text-red-700 dark:text-red-300">
          Error: {e.error_message}
        </p>
      )}
      {e.status === "SUCCESS" && e.output && (
        <div className="mt-2">
          <p className="mb-1 text-xs font-medium text-neutral-500">Output</p>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded bg-neutral-50 p-2 font-mono text-xs dark:bg-neutral-900">
{e.output}
          </pre>
        </div>
      )}
      {e.notes && (
        <p className="mt-2 text-xs text-neutral-500">Notes: {e.notes}</p>
      )}
    </li>
  );
}

/**
 * Experiment history + (owner only) "Run Experiment" against a chosen version.
 * Backend enforces owner-only execution regardless of what the UI shows.
 */
export function ExperimentSection({
  promptId,
  isOwner,
  currentVersionId,
  currentVersionNumber,
}: {
  promptId: string;
  isOwner: boolean;
  currentVersionId: string | null;
  currentVersionNumber: number | null;
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
        if (!cancelled) setExperiments(res.items);
      } catch (err) {
        if (!cancelled) setError(friendlyMessage(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [promptId, reloadKey]);

  return (
    <section aria-label="Experiments" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">Experiments</h2>
        {isOwner && currentVersionId && !showForm && (
          <button
            type="button"
            className={buttonPrimary}
            onClick={() => setShowForm(true)}
          >
            Run Experiment
          </button>
        )}
      </div>

      <p className="text-xs text-neutral-500">
        An experiment runs a specific immutable version&apos;s content against a
        model and stores the result for comparison.
      </p>

      {isOwner && showForm && currentVersionId && currentVersionNumber !== null && (
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
      {experiments === null && !error && <Spinner label="Loading experiments…" />}

      {experiments !== null && experiments.length === 0 && (
        <p className="rounded border border-dashed border-neutral-300 p-4 text-center text-sm text-neutral-500 dark:border-neutral-700">
          No experiments yet.
        </p>
      )}

      {experiments !== null && experiments.length > 0 && (
        <ul className="space-y-2">
          {experiments.map((e) => (
            <ExperimentRow key={e.experiment_id} e={e} />
          ))}
        </ul>
      )}
    </section>
  );
}
