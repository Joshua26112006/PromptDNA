"use client";

// PromptDNA design system primitives.
//
// No component library — Tailwind utilities over the semantic tokens declared
// in app/globals.css (surface / panel / line / ink / accent / status), plus
// semantic HTML with real labels, focus rings and non-colour-only status text.

import type {
  ComponentType,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  SVGProps,
  TextareaHTMLAttributes,
} from "react";
import { useId } from "react";

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

/* --------------------------------------------------------------------------
 * Surfaces
 * ----------------------------------------------------------------------- */

/** Raised panel: the default container for a block of content. */
export const card = "rounded-xl border border-line bg-panel";

/** Panel that is itself a link/button — adds hover affordance. */
export const cardInteractive =
  card +
  " transition duration-150 hover:border-line-strong hover:shadow-[0_1px_2px_rgba(16,18,24,0.04),0_8px_24px_-12px_rgba(16,18,24,0.18)]";

/** Inset well for code, model output, and other verbatim technical text. */
export const well = "rounded-lg border border-line bg-panel-muted";

export const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface";

/* --------------------------------------------------------------------------
 * Buttons
 * ----------------------------------------------------------------------- */

const buttonBase =
  "inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 h-9 text-sm font-medium " +
  "transition duration-150 disabled:opacity-50 disabled:pointer-events-none " +
  focusRing;

export const buttonPrimary =
  buttonBase +
  " bg-accent-solid text-white shadow-sm hover:bg-accent-solid-hover active:scale-[0.985]";

export const buttonSecondary =
  buttonBase +
  " border border-line-strong bg-panel text-ink hover:bg-panel-muted active:scale-[0.985]";

export const buttonGhost =
  buttonBase + " text-ink-muted hover:bg-panel-muted hover:text-ink";

/* --------------------------------------------------------------------------
 * Feedback
 * ----------------------------------------------------------------------- */

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-2.5 text-sm text-ink-muted">
      <span
        aria-hidden
        className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-line-strong border-t-accent"
      />
      <span>{label}</span>
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="flex items-start gap-2 rounded-lg border border-danger-line bg-danger-soft px-3.5 py-2.5 text-sm text-danger"
    >
      <AlertGlyph />
      <span>{message}</span>
    </p>
  );
}

function AlertGlyph() {
  return (
    <svg
      aria-hidden
      focusable="false"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="mt-0.5 h-4 w-4 shrink-0"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5M12 16.2h.01" />
    </svg>
  );
}

/** Inline explanatory note — neutral by default, or a status tone. */
export function Notice({
  tone = "info",
  icon: Icon,
  title,
  children,
}: {
  tone?: "info" | "accent" | "warn";
  icon?: IconType;
  title?: string;
  children: ReactNode;
}) {
  const tones = {
    info: "border-line bg-panel-muted text-ink-muted",
    accent: "border-accent-line bg-accent-soft text-accent-ink",
    warn: "border-warn-line bg-warn-soft text-warn",
  } as const;
  return (
    <div className={`flex items-start gap-2.5 rounded-lg border px-3.5 py-2.5 text-sm ${tones[tone]}`}>
      {Icon && <Icon className="mt-0.5 h-4 w-4 shrink-0" />}
      <div className="min-w-0">
        {title && <p className="font-medium text-ink">{title}</p>}
        <div className={title ? "mt-0.5" : undefined}>{children}</div>
      </div>
    </div>
  );
}

/** Kept for compatibility with existing call sites. */
export function InfoNote({ children }: { children: ReactNode }) {
  return <Notice tone="accent">{children}</Notice>;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-md bg-line ${className}`} />;
}

/* --------------------------------------------------------------------------
 * Empty state
 * ----------------------------------------------------------------------- */

/**
 * Every empty state explains the concept and offers the next action — these
 * double as the product's in-context teaching surface.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  compact = false,
}: {
  icon: IconType;
  title: string;
  description: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center rounded-xl border border-dashed border-line-strong bg-panel/60 text-center ${
        compact ? "px-5 py-7" : "px-6 py-12"
      }`}
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-full border border-line bg-panel text-ink-subtle">
        <Icon className="h-5 w-5" />
      </span>
      <p className="mt-3 text-sm font-semibold text-ink">{title}</p>
      <div className="mt-1 max-w-md text-sm text-ink-muted">{description}</div>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/* --------------------------------------------------------------------------
 * Structure
 * ----------------------------------------------------------------------- */

/** Page title block: eyebrow / title / description / actions. */
export function PageHeader({
  title,
  description,
  actions,
  meta,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  meta?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
      <div className="min-w-0 sm:flex-1">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm text-ink-muted">{description}</p>}
        {meta && <div className="mt-3">{meta}</div>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/**
 * A titled content region. Renders a real landmark (`<section aria-label>`) so
 * assistive tech — and the test suite — can address each area of the workspace.
 */
export function SectionCard({
  title,
  ariaLabel,
  description,
  icon: Icon,
  actions,
  bare = false,
  children,
}: {
  title: string;
  ariaLabel?: string;
  description?: ReactNode;
  icon?: IconType;
  actions?: ReactNode;
  /** drop the panel chrome and render the body flush (for nested lists) */
  bare?: boolean;
  children: ReactNode;
}) {
  return (
    <section aria-label={ariaLabel ?? title} className={bare ? undefined : card}>
      <div
        className={`flex flex-wrap items-start justify-between gap-x-4 gap-y-2 ${
          bare ? "pb-3" : "px-4 pt-4 pb-3 sm:px-5"
        }`}
      >
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-sm font-semibold tracking-tight text-ink">
            {Icon && <Icon className="h-4 w-4 shrink-0 text-ink-subtle" />}
            {title}
          </h2>
          {description && <p className="mt-1 max-w-prose text-xs text-ink-muted">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 gap-2">{actions}</div>}
      </div>
      <div className={bare ? undefined : "px-4 pb-4 sm:px-5 sm:pb-5"}>{children}</div>
    </section>
  );
}

/** Small labelled metric — used in the prompt detail stat strip. */
export function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon?: IconType;
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="flex items-center gap-2">
      {Icon && <Icon className="h-4 w-4 shrink-0 text-ink-subtle" />}
      <div className="min-w-0 leading-tight">
        <div className="truncate text-sm font-medium text-ink tnum">{value}</div>
        <div className="text-[11px] uppercase tracking-wide text-ink-subtle">{label}</div>
      </div>
    </div>
  );
}

/** Neutral metadata pill. */
export function Chip({
  icon: Icon,
  children,
  mono = false,
}: {
  icon?: IconType;
  children: ReactNode;
  mono?: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border border-line bg-panel-muted px-2 py-0.5 text-[11px] text-ink-muted ${
        mono ? "font-mono tnum" : ""
      }`}
    >
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </span>
  );
}

/* --------------------------------------------------------------------------
 * Form fields
 * ----------------------------------------------------------------------- */

export const fieldClass =
  "w-full rounded-lg border border-line-strong bg-panel px-3 py-2 text-sm text-ink shadow-sm " +
  "transition duration-150 placeholder:text-ink-subtle " +
  "focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25 " +
  "disabled:opacity-60";

const labelClass = "block text-sm font-medium text-ink";
const hintClass = "text-xs text-ink-muted";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function TextField({ label, hint, id, ...props }: TextFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  const hintId = hint ? `${fieldId}-hint` : undefined;
  return (
    <div className="space-y-1.5">
      <label htmlFor={fieldId} className={labelClass}>
        {label}
      </label>
      <input id={fieldId} aria-describedby={hintId} className={fieldClass} {...props} />
      {hint && (
        <p id={hintId} className={hintClass}>
          {hint}
        </p>
      )}
    </div>
  );
}

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
  /** render the control in monospace — for prompt content */
  mono?: boolean;
}

export function TextAreaField({ label, hint, id, mono = true, ...props }: TextAreaFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  const hintId = hint ? `${fieldId}-hint` : undefined;
  return (
    <div className="space-y-1.5">
      <label htmlFor={fieldId} className={labelClass}>
        {label}
      </label>
      <textarea
        id={fieldId}
        aria-describedby={hintId}
        className={`${fieldClass} ${mono ? "font-mono leading-relaxed" : ""}`}
        {...props}
      />
      {hint && (
        <p id={hintId} className={hintClass}>
          {hint}
        </p>
      )}
    </div>
  );
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  hint?: string;
}

export function SelectField({ label, hint, id, children, ...props }: SelectFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  const hintId = hint ? `${fieldId}-hint` : undefined;
  return (
    <div className="space-y-1.5">
      <label htmlFor={fieldId} className={labelClass}>
        {label}
      </label>
      <select id={fieldId} aria-describedby={hintId} className={fieldClass} {...props}>
        {children}
      </select>
      {hint && (
        <p id={hintId} className={hintClass}>
          {hint}
        </p>
      )}
    </div>
  );
}

/** Two-option radio group rendered as a labelled row (visibility, etc.). */
export function RadioRow({
  legend,
  hideLegend = false,
  name,
  options,
  value,
  onChange,
}: {
  legend: string;
  /** keep the legend for assistive tech when a visible heading already names the group */
  hideLegend?: boolean;
  name: string;
  options: { value: string; label: string; hint?: string }[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <fieldset className="space-y-1.5">
      <legend className={hideLegend ? "sr-only" : labelClass}>{legend}</legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {options.map((o) => {
          const selected = o.value === value;
          return (
            <label
              key={o.value}
              className={`flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 text-sm transition has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent ${
                selected
                  ? "border-accent-line bg-accent-soft text-accent-ink"
                  : "border-line bg-panel text-ink-muted hover:border-line-strong"
              }`}
            >
              <input
                type="radio"
                name={name}
                checked={selected}
                onChange={() => onChange(o.value)}
                className="mt-0.5 accent-[var(--accent-solid)]"
              />
              <span className="min-w-0">
                <span className={`block font-medium ${selected ? "text-accent-ink" : "text-ink"}`}>
                  {o.label}
                </span>
                {o.hint && <span className="block text-xs text-ink-muted">{o.hint}</span>}
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

/* --------------------------------------------------------------------------
 * Formatting
 * ----------------------------------------------------------------------- */

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

/** Compact absolute date — "5 Sep 2026" — for dense metadata rows. */
export function formatDay(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}
