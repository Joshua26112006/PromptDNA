import Link from "next/link";

import type { PromptListItem } from "@/lib/types";

import { LayersIcon } from "./icons";
import { cardInteractive, focusRing, formatDay } from "./ui";
import { VisibilityBadge } from "./VisibilityBadge";

export function PromptCard({
  prompt,
  ownedByViewer,
}: {
  prompt: PromptListItem;
  ownedByViewer: boolean;
}) {
  return (
    <li className="h-full">
      <Link
        href={`/prompts/${prompt.prompt_id}`}
        className={`group flex h-full flex-col ${cardInteractive} ${focusRing}`}
      >
        <div className="flex-1 p-4">
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-medium leading-snug text-ink transition-colors group-hover:text-accent">
              {prompt.title}
            </h3>
            <VisibilityBadge isPublic={prompt.is_public} />
          </div>

          {prompt.description ? (
            <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-ink-muted">
              {prompt.description}
            </p>
          ) : (
            <p className="mt-1.5 text-sm italic text-ink-subtle">No description</p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line px-4 py-2.5 text-xs text-ink-subtle">
          <span className="inline-flex items-center gap-1 font-mono tnum text-ink-muted">
            <LayersIcon className="h-3.5 w-3.5" />v{prompt.latest_version_number ?? "—"}
          </span>
          <span aria-hidden>·</span>
          <span>{ownedByViewer ? "Yours" : "Shared"}</span>
          <span aria-hidden>·</span>
          <span>Updated {formatDay(prompt.updated_at)}</span>
        </div>
      </Link>
    </li>
  );
}
