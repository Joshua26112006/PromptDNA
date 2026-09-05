import type { Version } from "@/lib/types";

import { card, formatDate } from "./ui";

/** Read-only display of a single version. Content is never editable here. */
export function VersionPanel({
  version,
  isCurrent,
  creatorIsViewer,
}: {
  version: Version;
  isCurrent: boolean;
  creatorIsViewer: boolean;
}) {
  return (
    <section aria-label={`Version ${version.version_number} details`} className={card}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-200 px-4 py-2.5 dark:border-neutral-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
            {isCurrent ? "Current version" : "Historical version"}
          </span>
          <span className="font-mono text-sm">Version {version.version_number}</span>
        </div>
        <span
          className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${
            isCurrent
              ? "border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-800/60 dark:bg-indigo-950/40 dark:text-indigo-300"
              : "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-300"
          }`}
        >
          {isCurrent ? "LATEST" : "IMMUTABLE"}
        </span>
      </header>

      <div className="space-y-3 p-4">
        <div>
          <p className="mb-1 text-xs font-medium text-neutral-500 dark:text-neutral-400">
            Prompt content
          </p>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-neutral-100 bg-neutral-50 p-3 font-mono text-sm dark:border-neutral-800/60 dark:bg-neutral-950">
{version.content}
          </pre>
        </div>

        <dl className="grid grid-cols-1 gap-1 text-xs text-neutral-500 dark:text-neutral-400 sm:grid-cols-2">
          <div>
            <dt className="inline font-medium">Change summary: </dt>
            <dd className="inline">{version.change_summary ?? "—"}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Created: </dt>
            <dd className="inline">{formatDate(version.created_at)}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Created by: </dt>
            <dd className="inline">{creatorIsViewer ? "you" : "another user"}</dd>
          </div>
        </dl>

        {!isCurrent && (
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Historical versions are immutable — they cannot be edited or deleted.
          </p>
        )}
      </div>
    </section>
  );
}
