"use client";

import { useEffect, useState } from "react";

import { friendlyMessage, listModels, runExperiment } from "@/lib/api";
import type { Experiment, Model } from "@/lib/types";

import { AlertTriangleIcon } from "./icons";
import {
  buttonPrimary,
  buttonSecondary,
  Chip,
  ErrorBox,
  Notice,
  SelectField,
  Skeleton,
  Spinner,
  TextField,
  well,
} from "./ui";

/**
 * Owner-only. Runs `POST .../versions/{versionId}/experiments` with only
 * `{ model_id, notes }`. The version under test is stated explicitly, because
 * an experiment is only meaningful next to the exact text it ran.
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

  const noneConfigured = models !== null && models.length > 0 && !models.some((m) => m.execution_configured);

  return (
    <form
      onSubmit={onSubmit}
      aria-label="Run experiment"
      className={`space-y-4 p-4 sm:p-5 ${well}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold text-ink">Run Experiment</h3>
        <Chip mono>Version {versionNumber}</Chip>
      </div>

      <p className="text-xs leading-relaxed text-ink-muted">
        Sends <span className="font-medium text-ink">Version {versionNumber}</span>&apos;s
        exact text to the selected model and stores the result. Nothing about the
        version changes.
      </p>

      {models === null ? (
        <div className="space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : (
        <>
          {noneConfigured && (
            <Notice tone="warn" icon={AlertTriangleIcon} title="No model is ready to run">
              Every registered model is missing provider credentials on the server,
              so experiments can&apos;t execute yet. Add credentials for a provider
              (or enable the built-in mock provider) and the model will become
              selectable here.
            </Notice>
          )}
          <SelectField
            id="exp-model"
            label="Model"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            hint="Models without credentials on this server can't be selected."
          >
            <option value="">Select a model…</option>
            {models.map((m) => (
              <option key={m.model_id} value={m.model_id} disabled={!m.execution_configured}>
                {m.name} ({m.provider})
                {m.execution_configured ? "" : " — not configured"}
              </option>
            ))}
          </SelectField>
        </>
      )}

      <TextField
        id="exp-notes"
        label="Notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional — what are you testing?"
      />

      {running && <Spinner label="Running experiment…" />}
      {error && <ErrorBox message={error} />}

      <div className="flex flex-wrap gap-2">
        <button type="submit" className={buttonPrimary} disabled={running || noneConfigured}>
          {running ? "Running…" : "Run Experiment"}
        </button>
        <button type="button" className={buttonSecondary} onClick={onCancel} disabled={running}>
          Cancel
        </button>
      </div>
    </form>
  );
}
