"use client";

import type { Version } from "@/lib/types";

import { formatDate } from "./ui";

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
      <h2 className="mb-2 text-sm font-semibold">Version history</h2>
      <ol className="divide-y divide-neutral-200 rounded border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
        {ordered.map((v) => {
          const isCurrent = v.version_number === latestNumber;
          const isSelected = v.version_id === selectedId;
          return (
            <li key={v.version_id}>
              <button
                type="button"
                aria-current={isSelected ? "true" : undefined}
                onClick={() => onSelect(v.version_id)}
                className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-neutral-500 ${
                  isSelected
                    ? "bg-neutral-100 dark:bg-neutral-800"
                    : "hover:bg-neutral-50 dark:hover:bg-neutral-900"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="font-mono">Version {v.version_number}</span>
                  {isCurrent && (
                    <span className="rounded border border-neutral-400 px-1 text-[10px] font-semibold text-neutral-600 dark:border-neutral-600 dark:text-neutral-300">
                      CURRENT
                    </span>
                  )}
                </span>
                <span className="truncate text-xs text-neutral-500">
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
