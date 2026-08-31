"use client";

import { useState } from "react";

import { friendlyMessage, updatePromptMetadata } from "@/lib/api";
import type { Prompt, PromptMetadataPayload } from "@/lib/types";

import {
  buttonPrimary,
  buttonSecondary,
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
      className="space-y-3 rounded border border-neutral-300 p-4 dark:border-neutral-700"
    >
      <h3 className="text-sm font-semibold">Edit prompt metadata</h3>
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
      <fieldset>
        <legend className="text-sm font-medium">Visibility</legend>
        <label className="mr-4 inline-flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="visibility"
            checked={!isPublic}
            onChange={() => setIsPublic(false)}
          />
          Private
        </label>
        <label className="inline-flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="visibility"
            checked={isPublic}
            onChange={() => setIsPublic(true)}
          />
          Public
        </label>
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
