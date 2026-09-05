"use client";

import type { Version } from "@/lib/types";

import { focusRing, formatDay } from "./ui";

/**
 * Version lineage, newest first, drawn as a connected timeline — the visual
 * spine of the product. Selecting a node swaps the version shown beside it.
 *
 * There are deliberately no edit/delete affordances anywhere here: versions are
 * immutable, and the UI should never imply otherwise.
 */
export function VersionTimeline({
  versions,
  latestNumber,
  selectedId,
  onSelect,
}: {
  versions: Version[];
  latestNumber: number | null;
  selectedId: string | null;
  onSelect: (versionId: string) => void;
}) {
  const ordered = [...versions].sort((a, b) => b.version_number - a.version_number);

  return (
    <section aria-label="Version history">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-tight text-ink">Version history</h2>
        <span className="text-xs text-ink-subtle tnum">
          {ordered.length} {ordered.length === 1 ? "version" : "versions"}
        </span>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-ink-muted">
        Every edit is kept. Select a version to read exactly what it said.
      </p>

      <ol className="mt-3">
        {ordered.map((v, i) => {
          const isCurrent = v.version_number === latestNumber;
          const isSelected = v.version_id === selectedId;
          const isLast = i === ordered.length - 1;
          return (
            <li key={v.version_id} className="relative pl-6">
              {!isLast && (
                <span
                  aria-hidden
                  className="absolute bottom-0 left-[6px] top-6 w-px bg-line-strong"
                />
              )}
              <span
                aria-hidden
                className={`absolute left-0 top-[18px] h-3 w-3 rounded-full border-2 transition ${
                  isSelected
                    ? "border-accent bg-accent"
                    : isCurrent
                      ? "border-accent bg-panel"
                      : "border-line-strong bg-panel"
                }`}
              />
              <button
                type="button"
                aria-current={isSelected ? "true" : undefined}
                onClick={() => onSelect(v.version_id)}
                className={`my-0.5 w-full rounded-lg px-2.5 py-2 text-left transition ${focusRing} ${
                  isSelected ? "bg-accent-soft" : "hover:bg-panel-muted"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span
                    className={`font-mono text-sm tnum ${
                      isSelected ? "font-semibold text-accent-ink" : "text-ink"
                    }`}
                  >
                    Version {v.version_number}
                  </span>
                  {isCurrent && (
                    <span className="rounded-full border border-accent-line bg-accent-soft px-1.5 py-px text-[10px] font-semibold uppercase tracking-wider text-accent-ink">
                      CURRENT
                    </span>
                  )}
                </span>
                <span className="mt-0.5 block truncate text-xs text-ink-muted">
                  {v.change_summary ?? "No change summary"}
                </span>
                <span className="mt-0.5 block text-[11px] text-ink-subtle">
                  {formatDay(v.created_at)}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
