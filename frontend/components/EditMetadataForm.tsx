"use client";

import { useState } from "react";

import { friendlyMessage, updatePromptMetadata } from "@/lib/api";
import type { Prompt, PromptMetadataPayload } from "@/lib/types";

import { InfoIcon } from "./icons";
import {
  buttonPrimary,
  buttonSecondary,
  card,
  ErrorBox,
  Notice,
  RadioRow,
  TextAreaField,
  TextField,
} from "./ui";

/**
 * Owner-only. `PATCH /api/v1/prompts/{id}` with metadata fields only — never
 * creates a version and never touches version content.
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
      className={`space-y-4 p-4 sm:p-5 ${card}`}
    >
      <h3 className="text-sm font-semibold text-ink">Edit prompt metadata</h3>

      <Notice icon={InfoIcon}>
        Metadata describes the prompt; it isn&apos;t part of any version. Saving
        here does not create a version and leaves all prompt text untouched.
      </Notice>

      <TextField
        label="Title"
        required
        maxLength={200}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <TextAreaField
        label="Description"
        mono={false}
        rows={2}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <TextAreaField
        label="Purpose"
        mono={false}
        rows={2}
        value={purpose}
        onChange={(e) => setPurpose(e.target.value)}
      />
      <RadioRow
        legend="Visibility"
        name="visibility"
        value={isPublic ? "public" : "private"}
        onChange={(v) => setIsPublic(v === "public")}
        options={[
          { value: "private", label: "Private", hint: "Only you can see it." },
          { value: "public", label: "Public", hint: "Any signed-in user can view it." },
        ]}
      />

      {error && <ErrorBox message={error} />}

      <div className="flex flex-wrap gap-2">
        <button type="submit" className={buttonPrimary} disabled={busy}>
          {busy ? "Saving…" : "Save changes"}
        </button>
        <button type="button" className={buttonSecondary} onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </form>
  );
}
