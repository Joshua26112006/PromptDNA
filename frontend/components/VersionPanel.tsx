import type { Version } from "@/lib/types";

import { LockIcon } from "./icons";
import { card, formatDate, well } from "./ui";

/**
 * Read-only view of one version. Content is never editable here and this panel
 * intentionally contains no controls — a version, once written, is a fixed
 * historical record.
 */
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
      <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-line px-4 py-3 sm:px-5">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-mono text-sm font-semibold text-ink tnum">
            Version {version.version_number}
          </h2>
          {isCurrent && (
            <span className="rounded-full border border-accent-line bg-accent-soft px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-accent-ink">
              Latest
            </span>
          )}
          <span className="inline-flex items-center gap-1 rounded-full border border-line bg-panel-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
            <LockIcon className="h-3 w-3" />
            Immutable
          </span>
        </div>
        <p className="text-xs text-ink-subtle">
          {isCurrent ? "Newest version of this prompt" : "An earlier version, kept for comparison"}
        </p>
      </header>

      <div className="space-y-4 p-4 sm:p-5">
        <div>
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-ink-subtle">
            Prompt content
          </p>
          <pre className={`max-h-[28rem] overflow-auto whitespace-pre-wrap break-words p-3.5 font-mono text-sm leading-relaxed text-ink ${well}`}>{version.content}</pre>
        </div>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 border-t border-line pt-4 sm:grid-cols-3">
          <div className="col-span-2 sm:col-span-1">
            <dt className="text-[11px] uppercase tracking-wide text-ink-subtle">Change summary</dt>
            <dd className="mt-0.5 text-sm text-ink">{version.change_summary ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-ink-subtle">Created</dt>
            <dd className="mt-0.5 text-sm text-ink">{formatDate(version.created_at)}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-ink-subtle">Created by</dt>
            <dd className="mt-0.5 text-sm text-ink">
              {creatorIsViewer ? "You" : "Another user"}
            </dd>
          </div>
        </dl>

        <p className="text-xs leading-relaxed text-ink-muted">
          Versions are immutable — this text can never be edited or deleted. Changing
          the prompt creates a new version instead, so every experiment stays tied to
          the exact wording it ran against.
        </p>
      </div>
    </section>
  );
}
