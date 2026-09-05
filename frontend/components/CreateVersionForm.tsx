"use client";

import { useState } from "react";

import { createVersion, friendlyMessage } from "@/lib/api";
import type { Version } from "@/lib/types";

import { buttonPrimary, buttonSecondary, card, ErrorBox, TextAreaField, TextField } from "./ui";

/**
 * Owner-only. Submits `POST /api/v1/prompts/{id}/versions` with ONLY
 * `content` + `change_summary`. The backend assigns the version number and
 * creator.
 */
export function CreateVersionForm({
  promptId,
  onCreated,
  onCancel,
}: {
  promptId: string;
  onCreated: (version: Version) => void;
  onCancel: () => void;
}) {
  const [content, setContent] = useState("");
  const [changeSummary, setChangeSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const version = await createVersion(promptId, {
        content,
        change_summary: changeSummary.trim() ? changeSummary : null,
      });
      onCreated(version);
    } catch (err) {
      setError(friendlyMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      aria-label="Create new version"
      className={`space-y-3 p-4 ${card}`}
    >
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        Create new version
      </h3>
      <TextAreaField
        label="New prompt content"
        required
        rows={8}
        value={content}
        onChange={(e) => setContent(e.target.value)}
      />
      <TextField
        label="Change summary"
        hint="Optional — a short note about what changed."
        value={changeSummary}
        onChange={(e) => setChangeSummary(e.target.value)}
      />
      {error && <ErrorBox message={error} />}
      <div className="flex gap-2">
        <button type="submit" className={buttonPrimary} disabled={busy}>
          {busy ? "Creating…" : "Create version"}
        </button>
        <button
          type="button"
          className={buttonSecondary}
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
