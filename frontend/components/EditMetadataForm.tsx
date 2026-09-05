"use client";

import { useState } from "react";

import { friendlyMessage, updatePromptMetadata } from "@/lib/api";
import type { Prompt, PromptMetadataPayload } from "@/lib/types";

import {
  buttonPrimary,
  buttonSecondary,
  card,
  ErrorBox,
  InfoNote,
  TextAreaField,
  TextField,
} from "./ui";

/**
 * Owner-only. `PATCH /api/v1/prompts/{id}` with metadata fields only. This
 * never creates a version and never touches version content.
 */
export function EditMetadataForm({
  prompt,
  onSaved,
  onCancel,
}: {
  prompt: Prompt;
  onSaved: (updated: Prompt) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(prompt.title);
  const [description, setDescription] = useState(prompt.description ?? "");
  const [purpose, setPurpose] = useState(prompt.purpose ?? "");
  const [isPublic, setIsPublic] = useState(prompt.is_public);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const payload: PromptMetadataPayload = {
      title,
      description: description.trim() ? description : null,
      purpose: purpose.trim() ? purpose : null,
      is_public: isPublic,
    };
    try {
      const updated = await updatePromptMetadata(prompt.prompt_id, payload);
      onSaved(updated);
    } catch (err) {
      setError(friendlyMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      aria-label="Edit prompt metadata"
      className={`space-y-3 p-4 ${card}`}
    >
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        Edit prompt metadata
      </h3>
      <InfoNote>
        Editing metadata does not create a new version. Prompt content lives in
        versions and stays unchanged.
      </InfoNote>
      <TextField
        label="Title"
        required
        maxLength={200}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <TextAreaField
        label="Description"
        rows={2}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <TextAreaField
        label="Purpose"
        rows={2}
        value={purpose}
        onChange={(e) => setPurpose(e.target.value)}
      />
      <fieldset className="space-y-1.5">
        <legend className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
          Visibility
        </legend>
        <div className="flex gap-4">
          <label className="inline-flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
            <input
              type="radio"
              name="visibility"
              checked={!isPublic}
              onChange={() => setIsPublic(false)}
              className="accent-indigo-600"
            />
            Private
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
            <input
              type="radio"
              name="visibility"
              checked={isPublic}
              onChange={() => setIsPublic(true)}
              className="accent-indigo-600"
            />
            Public
          </label>
        </div>
      </fieldset>
      {error && <ErrorBox message={error} />}
      <div className="flex gap-2">
        <button type="submit" className={buttonPrimary} disabled={busy}>
          {busy ? "Saving…" : "Save changes"}
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
