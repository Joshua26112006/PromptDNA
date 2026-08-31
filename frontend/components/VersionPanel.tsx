import type { Version } from "@/lib/types";

import { formatDate } from "./ui";

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
    <section
      aria-label={`Version ${version.version_number} details`}
      className="rounded border border-neutral-200 dark:border-neutral-800"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-200 px-4 py-2 dark:border-neutral-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            {isCurrent ? "Current version" : "Historical version"}
          </span>
          <span className="font-mono text-sm">Version {version.version_number}</span>
        </div>
        <span
          className={`rounded border px-1.5 py-0.5 text-[11px] font-semibold ${
            isCurrent
              ? "border-neutral-400 text-neutral-600 dark:border-neutral-600 dark:text-neutral-300"
              : "border-amber-400 text-amber-700 dark:border-amber-700 dark:text-amber-300"
          }`}
        >
          {isCurrent ? "LATEST" : "IMMUTABLE"}
        </span>
      </header>

      <div className="space-y-3 p-4">
        <div>
          <p className="mb-1 text-xs font-medium text-neutral-500">Prompt content</p>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded bg-neutral-50 p-3 font-mono text-sm dark:bg-neutral-900">
{version.content}
          </pre>
        </div>

        <dl className="grid grid-cols-1 gap-1 text-xs text-neutral-500 sm:grid-cols-2">
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
          <p className="text-xs text-neutral-500">
            Historical versions are immutable — they cannot be edited or deleted.
          </p>
        )}
      </div>
    </section>
  );
}
