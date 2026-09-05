"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ArrowLeftIcon, InfoIcon } from "@/components/icons";
import {
  buttonPrimary,
  buttonSecondary,
  card,
  ErrorBox,
  focusRing,
  Notice,
  RadioRow,
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
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <Link
          href="/prompts"
          className={`inline-flex items-center gap-1.5 rounded text-sm text-ink-muted transition-colors hover:text-ink ${focusRing}`}
        >
          <ArrowLeftIcon className="h-3.5 w-3.5" />
          Back to Prompt Library
        </Link>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink">New Prompt</h1>
        <p className="mt-1.5 text-sm text-ink-muted">
          A prompt is a reusable instruction for a model. Its text lives in
          versions — the content you write below is saved as{" "}
          <span className="font-medium text-ink">Version 1</span>.
        </p>
      </div>

      <form onSubmit={onSubmit} aria-label="Create prompt" className="space-y-6">
        <div className={`space-y-4 p-4 sm:p-5 ${card}`}>
          <h2 className="text-sm font-semibold text-ink">Details</h2>
          <TextField
            label="Title"
            required
            maxLength={200}
            placeholder="Academic paper summariser"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <TextAreaField
            label="Description"
            mono={false}
            rows={2}
            hint="Optional — a one-line summary shown in the library."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <TextAreaField
            label="Purpose"
            mono={false}
            rows={2}
            hint="Optional — what this prompt is for, and when to reach for it."
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
          />
        </div>

        <div className={`space-y-4 p-4 sm:p-5 ${card}`}>
          <h2 className="text-sm font-semibold text-ink">Prompt text</h2>
          <TextAreaField
            label="Prompt Content"
            required
            rows={12}
            placeholder="You are an expert reviewer. Summarise the following abstract in three bullet points…"
            hint="Saved as Version 1. Editing later never overwrites this — it creates a new version."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>

        <div className={`space-y-4 p-4 sm:p-5 ${card}`}>
          <h2 className="text-sm font-semibold text-ink">Visibility</h2>
          <RadioRow
            legend="Visibility"
            hideLegend
            name="visibility"
            value={isPublic ? "public" : "private"}
            onChange={(v) => setIsPublic(v === "public")}
            options={[
              { value: "private", label: "Private", hint: "Only you can see it." },
              { value: "public", label: "Public", hint: "Any signed-in user can view it." },
            ]}
          />
          <Notice icon={InfoIcon}>
            Visibility can be changed at any time, and only ever affects who can{" "}
            <em>read</em> the prompt — you remain the only person who can edit it or
            run experiments on it.
          </Notice>
        </div>

        {error && <ErrorBox message={error} />}

        <div className="flex flex-wrap gap-2">
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
