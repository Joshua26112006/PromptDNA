"use client";

import { useEffect, useState } from "react";

import { friendlyMessage, listModels, runExperiment } from "@/lib/api";
import type { Experiment, Model } from "@/lib/types";

import { buttonPrimary, buttonSecondary, card, ErrorBox, Spinner, TextField } from "./ui";

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
      className={`space-y-3 p-4 ${card}`}
    >
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold">Run Experiment</h3>
        <span className="rounded-full border border-neutral-200 bg-neutral-50 px-1.5 py-0.5 font-mono text-xs text-neutral-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-400">
          Version {versionNumber}
        </span>
      </div>
      <p className="text-xs text-neutral-500 dark:text-neutral-400">
        This runs <strong>Version {versionNumber}</strong>&apos;s exact content
        against the selected model and records the result.
      </p>

      {models === null ? (
        <Spinner label="Loading models…" />
      ) : (
        <div className="space-y-1.5">
          <label htmlFor="exp-model" className="block text-sm font-medium text-neutral-800 dark:text-neutral-200">
            Model
          </label>
          <select
            id="exp-model"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 dark:border-neutral-700 dark:bg-neutral-900"
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

      <TextField
        id="exp-notes"
        label="Notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional"
      />

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
