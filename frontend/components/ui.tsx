"use client";

// Tiny shared UI primitives. No component library — just Tailwind + semantic
// HTML with accessible labels, focus states, and non-colour-only status text.

import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";
import { useId } from "react";

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-2 text-sm text-neutral-500"
    >
      <span
        aria-hidden
        className="h-4 w-4 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent"
      />
      <span>{label}</span>
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-300"
    >
      {message}
    </p>
  );
}

export function InfoNote({ children }: { children: ReactNode }) {
  return (
    <p className="rounded border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-400">
      {children}
    </p>
  );
}

const fieldClass =
  "w-full rounded border border-neutral-300 bg-transparent px-3 py-2 text-sm " +
  "focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500 " +
  "dark:border-neutral-700";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function TextField({ label, hint, id, ...props }: TextFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  return (
    <div className="space-y-1">
      <label htmlFor={fieldId} className="block text-sm font-medium">
        {label}
      </label>
      <input id={fieldId} className={fieldClass} {...props} />
      {hint && <p className="text-xs text-neutral-500">{hint}</p>}
    </div>
  );
}

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
}

export function TextAreaField({ label, hint, id, ...props }: TextAreaFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  return (
    <div className="space-y-1">
      <label htmlFor={fieldId} className="block text-sm font-medium">
        {label}
      </label>
      <textarea id={fieldId} className={`${fieldClass} font-mono`} {...props} />
      {hint && <p className="text-xs text-neutral-500">{hint}</p>}
    </div>
  );
}

export const buttonPrimary =
  "inline-flex items-center justify-center rounded bg-neutral-900 px-3 py-2 text-sm " +
  "font-medium text-white transition-colors hover:bg-neutral-700 disabled:opacity-50 " +
  "focus:outline-none focus:ring-2 focus:ring-neutral-500 focus:ring-offset-2 " +
  "dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200 dark:focus:ring-offset-neutral-950";

export const buttonSecondary =
  "inline-flex items-center justify-center rounded border border-neutral-300 px-3 py-2 " +
  "text-sm font-medium transition-colors hover:bg-neutral-100 disabled:opacity-50 " +
  "focus:outline-none focus:ring-2 focus:ring-neutral-500 focus:ring-offset-2 " +
  "dark:border-neutral-700 dark:hover:bg-neutral-900 dark:focus:ring-offset-neutral-950";

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
