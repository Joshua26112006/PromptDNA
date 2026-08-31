import Link from "next/link";

import type { PromptListItem } from "@/lib/types";

import { formatDate } from "./ui";
import { VisibilityBadge } from "./VisibilityBadge";

export function PromptCard({
  prompt,
  ownedByViewer,
}: {
  prompt: PromptListItem;
  ownedByViewer: boolean;
}) {
  return (
    <li>
      <Link
        href={`/prompts/${prompt.prompt_id}`}
        className="block rounded border border-neutral-200 p-4 transition-colors hover:border-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-500 dark:border-neutral-800 dark:hover:border-neutral-600"
      >
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-medium leading-snug">{prompt.title}</h3>
          <VisibilityBadge isPublic={prompt.is_public} />
        </div>

        {prompt.description && (
          <p className="mt-1 line-clamp-2 text-sm text-neutral-600 dark:text-neutral-400">
            {prompt.description}
          </p>
        )}

        <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-500">
          <div>
            <dt className="inline">Latest&nbsp;version: </dt>
            <dd className="inline font-mono">
              {prompt.latest_version_number ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="inline">Updated: </dt>
            <dd className="inline">{formatDate(prompt.updated_at)}</dd>
          </div>
          <div>
            <dt className="inline">Owner: </dt>
            <dd className="inline">{ownedByViewer ? "you" : "another user"}</dd>
          </div>
        </dl>
        <span className="mt-2 inline-block text-xs font-medium text-neutral-700 underline dark:text-neutral-300">
          View prompt →
        </span>
      </Link>
    </li>
  );
}
