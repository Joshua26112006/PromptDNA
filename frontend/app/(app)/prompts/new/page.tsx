"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ArrowLeftIcon } from "@/components/icons";
import {
  buttonPrimary,
  buttonSecondary,
  card,
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
        <Link
          href="/prompts"
          className="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-800 hover:underline dark:hover:text-neutral-200"
        >
          <ArrowLeftIcon className="h-3.5 w-3.5" />
          Back to Prompt Library
        </Link>
        <h1 className="mt-2 text-xl font-semibold text-neutral-900 dark:text-neutral-50">
          New Prompt
        </h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Creating a prompt also creates its <strong>Version 1</strong> from the
          content below. The prompt is owned by you.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        aria-label="Create prompt"
        className={`space-y-4 p-5 ${card}`}
      >
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
