"use client";

import { SearchIcon, SparklesIcon } from "./icons";

export type SearchMode = "lexical" | "semantic";

const MODES = [
  {
    value: "lexical" as const,
    icon: SearchIcon,
    label: "Search by text",
    hint: "Matches the words in a prompt's title.",
  },
  {
    value: "semantic" as const,
    icon: SparklesIcon,
    label: "Semantic Search",
    hint: "Matches meaning, even when the wording is different.",
  },
];

/**
 * The two retrieval modes side by side. Presented as equal-weight options with
 * their own explanation so the difference between matching *words* and matching
 * *meaning* is visible in the interface itself.
 */
export function SearchModeToggle({
  mode,
  onChange,
}: {
  mode: SearchMode;
  onChange: (mode: SearchMode) => void;
}) {
  return (
    <fieldset>
      <legend className="sr-only">Search mode</legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {MODES.map((m) => {
          const active = mode === m.value;
          return (
            <label
              key={m.value}
              className={`flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 transition has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent ${
                active
                  ? "border-accent-line bg-accent-soft"
                  : "border-line bg-panel hover:border-line-strong"
              }`}
            >
              <input
                type="radio"
                name="search-mode"
                className="sr-only"
                checked={active}
                onChange={() => onChange(m.value)}
              />
              <m.icon
                className={`mt-0.5 h-4 w-4 shrink-0 ${active ? "text-accent" : "text-ink-subtle"}`}
              />
              <span className="min-w-0">
                <span
                  className={`block text-sm font-medium ${active ? "text-accent-ink" : "text-ink"}`}
                >
                  {m.label}
                </span>
                <span className="mt-0.5 block text-xs leading-relaxed text-ink-muted">{m.hint}</span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
