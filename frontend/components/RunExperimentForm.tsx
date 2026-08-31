"use client";

import { useEffect, useState } from "react";

import { friendlyMessage, listModels, runExperiment } from "@/lib/api";
import type { Experiment, Model } from "@/lib/types";

import { buttonPrimary, buttonSecondary, ErrorBox, Spinner } from "./ui";

/**
 * Owner-only. Runs `POST .../versions/{versionId}/experiments` with only
 * `{ model_id, notes }`. The version being tested is shown explicitly (for
 * reproducibility). Backend assigns everything else.
 */
export function RunExperimentForm({
  promptId,
  versionId,
  versionNumber,
  onComplete,
  onCancel,
}: {
  promptId: string;
  versionId: string;
  versionNumber: number;
  onComplete: (experiment: Experiment) => void;
  onCancel: () => void;
}) {
  const [models, setModels] = useState<Model[] | null>(null);
  const [modelId, setModelId] = useState("");
  const [notes, setNotes] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listModels()
      .then((m) => {
        if (cancelled) return;
        setModels(m);
        const firstRunnable = m.find((x) => x.execution_configured);
        if (firstRunnable) setModelId(firstRunnable.model_id);
      })
      .catch((err) => {
        if (!cancelled) setError(friendlyMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!modelId) {
      setError("Choose a model.");
      return;
    }
    setError(null);
    setRunning(true);
    try {
      const experiment = await runExperiment(promptId, versionId, {
        model_id: modelId,
        notes: notes.trim() ? notes : null,
      });
      onComplete(experiment);
    } catch (err) {
      setError(friendlyMessage(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      aria-label="Run experiment"
      className="space-y-3 rounded border border-neutral-300 p-4 dark:border-neutral-700"
    >
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold">Run Experiment</h3>
        <span className="font-mono text-xs text-neutral-500">
          Version {versionNumber}
        </span>
      </div>
      <p className="text-xs text-neutral-500">
        This runs <strong>Version {versionNumber}</strong>&apos;s exact content
        against the selected model and records the result.
      </p>

      {models === null ? (
        <Spinner label="Loading models…" />
      ) : (
        <div className="space-y-1">
          <label htmlFor="exp-model" className="block text-sm font-medium">
            Model
          </label>
          <select
            id="exp-model"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            className="w-full rounded border border-neutral-300 bg-transparent px-3 py-2 text-sm dark:border-neutral-700"
          >
            <option value="">Select a model…</option>
            {models.map((m) => (
              <option
                key={m.model_id}
                value={m.model_id}
                disabled={!m.execution_configured}
              >
                {m.name} ({m.provider})
                {m.execution_configured ? "" : " — not configured"}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="space-y-1">
        <label htmlFor="exp-notes" className="block text-sm font-medium">
          Notes
        </label>
        <input
          id="exp-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full rounded border border-neutral-300 bg-transparent px-3 py-2 text-sm dark:border-neutral-700"
          placeholder="Optional"
        />
      </div>

      {running && <Spinner label="Running experiment…" />}
      {error && <ErrorBox message={error} />}

      <div className="flex gap-2">
        <button type="submit" className={buttonPrimary} disabled={running}>
          {running ? "Running…" : "Run Experiment"}
        </button>
        <button
          type="button"
          className={buttonSecondary}
          onClick={onCancel}
          disabled={running}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
