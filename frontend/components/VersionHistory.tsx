"use client";

import type { Version } from "@/lib/types";

import { card, formatDate } from "./ui";

/**
 * Selectable list of every version, newest first. The latest is marked
 * "CURRENT". There are deliberately no edit/delete controls anywhere here —
 * versions are immutable.
 */
export function VersionHistory({
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
  const ordered = [...versions].sort(
    (a, b) => b.version_number - a.version_number,
  );

  return (
    <section aria-label="Version history">
      <h2 className="mb-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        Version history
      </h2>
      <ol className={`divide-y divide-neutral-200 overflow-hidden dark:divide-neutral-800 ${card}`}>
        {ordered.map((v) => {
          const isCurrent = v.version_number === latestNumber;
          const isSelected = v.version_id === selectedId;
          return (
            <li key={v.version_id}>
              <button
                type="button"
                aria-current={isSelected ? "true" : undefined}
                onClick={() => onSelect(v.version_id)}
                className={`flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-left text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500 ${
                  isSelected
                    ? "bg-indigo-50 dark:bg-indigo-950/40"
                    : "hover:bg-neutral-50 dark:hover:bg-neutral-800/60"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="font-mono">Version {v.version_number}</span>
                  {isCurrent && (
                    <span className="rounded-full border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:border-indigo-800/60 dark:bg-indigo-950/40 dark:text-indigo-300">
                      CURRENT
                    </span>
                  )}
                </span>
                <span className="truncate text-xs text-neutral-500 dark:text-neutral-400">
                  {v.change_summary ?? formatDate(v.created_at)}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
