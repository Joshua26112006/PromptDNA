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
      className="flex items-center gap-2.5 text-sm text-neutral-500 dark:text-neutral-400"
    >
      <span
        aria-hidden
        className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600 dark:border-indigo-950 dark:border-t-indigo-400"
      />
      <span>{label}</span>
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-800 shadow-sm dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300"
    >
      {message}
    </p>
  );
}

export function InfoNote({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg border border-indigo-100 bg-indigo-50/70 px-3.5 py-2.5 text-sm text-indigo-900 dark:border-indigo-900/50 dark:bg-indigo-950/30 dark:text-indigo-200">
      {children}
    </p>
  );
}

export const fieldClass =
  "w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 shadow-sm transition-shadow placeholder:text-neutral-400 " +
  "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 " +
  "dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100 dark:placeholder:text-neutral-600";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function TextField({ label, hint, id, ...props }: TextFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  return (
    <div className="space-y-1.5">
      <label htmlFor={fieldId} className="block text-sm font-medium text-neutral-800 dark:text-neutral-200">
        {label}
      </label>
      <input id={fieldId} className={fieldClass} {...props} />
      {hint && <p className="text-xs text-neutral-500 dark:text-neutral-400">{hint}</p>}
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
    <div className="space-y-1.5">
      <label htmlFor={fieldId} className="block text-sm font-medium text-neutral-800 dark:text-neutral-200">
        {label}
      </label>
      <textarea id={fieldId} className={`${fieldClass} font-mono`} {...props} />
      {hint && <p className="text-xs text-neutral-500 dark:text-neutral-400">{hint}</p>}
    </div>
  );
}

export const buttonPrimary =
  "inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm " +
  "font-medium text-white shadow-sm transition-all hover:bg-indigo-500 hover:shadow active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 " +
  "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 " +
  "dark:focus:ring-offset-neutral-950";

export const buttonSecondary =
  "inline-flex items-center justify-center gap-1.5 rounded-lg border border-neutral-300 bg-white px-3.5 py-2 " +
  "text-sm font-medium text-neutral-800 shadow-sm transition-all hover:border-neutral-400 hover:bg-neutral-50 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 " +
  "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 " +
  "dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200 dark:hover:border-neutral-600 dark:hover:bg-neutral-800 dark:focus:ring-offset-neutral-950";

/** Shared card surface — used for list items, panels, and form containers. */
export const card =
  "rounded-xl border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-900";

/** Same surface, plus hover affordance for cards that are whole-card links. */
export const cardInteractive =
  card +
  " transition-all hover:-translate-y-0.5 hover:border-neutral-300 hover:shadow-md dark:hover:border-neutral-700";

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
