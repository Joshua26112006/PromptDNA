import Link from "next/link";

import type { PromptListItem } from "@/lib/types";

import { ChevronRightIcon, LayersIcon } from "./icons";
import { cardInteractive, formatDate } from "./ui";
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
        className={`block p-4 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${cardInteractive}`}
      >
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-medium leading-snug text-neutral-900 dark:text-neutral-50">
            {prompt.title}
          </h3>
          <VisibilityBadge isPublic={prompt.is_public} />
        </div>

        {prompt.description && (
          <p className="mt-1.5 line-clamp-2 text-sm text-neutral-600 dark:text-neutral-400">
            {prompt.description}
          </p>
        )}

        <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-500 dark:text-neutral-400">
          <div className="inline-flex items-center gap-1">
            <LayersIcon className="h-3 w-3" />
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
        <span className="mt-3 inline-flex items-center gap-0.5 text-xs font-medium text-indigo-600 dark:text-indigo-400">
          View prompt
          <ChevronRightIcon className="h-3 w-3" />
        </span>
      </Link>
    </li>
  );
}
