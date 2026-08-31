"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  buttonPrimary,
  buttonSecondary,
  ErrorBox,
  TextAreaField,
  TextField,
} from "@/components/ui";
import { createPrompt, friendlyMessage } from "@/lib/api";

export default function NewPromptPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [purpose, setPurpose] = useState("");
  const [content, setContent] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const prompt = await createPrompt({
        title,
        content,
        description: description.trim() ? description : null,
        purpose: purpose.trim() ? purpose : null,
        is_public: isPublic,
      });
      router.push(`/prompts/${prompt.prompt_id}`);
    } catch (err) {
      setError(friendlyMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <Link href="/prompts" className="text-sm text-neutral-500 hover:underline">
          ← Back to Prompt Library
        </Link>
        <h1 className="mt-1 text-xl font-semibold">New Prompt</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Creating a prompt also creates its <strong>Version 1</strong> from the
          content below. The prompt is owned by you.
        </p>
      </div>

      <form onSubmit={onSubmit} aria-label="Create prompt" className="space-y-4">
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
          hint="Optional."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <TextAreaField
          label="Purpose"
          rows={2}
          hint="Optional — what this prompt is for."
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
        />
        <TextAreaField
          label="Prompt Content"
          required
          rows={10}
          hint="Stored as Version 1. Prompt content is versioned — later edits create new versions."
          value={content}
          onChange={(e) => setContent(e.target.value)}
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
            {busy ? "Creating…" : "Create prompt"}
          </button>
          <Link href="/prompts" className={buttonSecondary}>
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
