"use client";

import { ChevronLeftIcon, ChevronRightIcon } from "./icons";
import { buttonSecondary } from "./ui";

interface PaginationProps {
  offset: number;
  limit: number;
  total: number;
  onChange: (nextOffset: number) => void;
}

export function Pagination({ offset, limit, total, onChange }: PaginationProps) {
  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;
  if (!hasPrev && !hasNext) return null;

  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);

  return (
    <nav className="flex items-center justify-between gap-3 text-sm" aria-label="Pagination">
      <span className="text-ink-muted tnum" aria-live="polite">
        {from}–{to} of {total}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className={buttonSecondary}
          onClick={() => onChange(Math.max(0, offset - limit))}
          disabled={!hasPrev}
        >
          <ChevronLeftIcon className="h-3.5 w-3.5" />
          Previous
        </button>
        <button
          type="button"
          className={buttonSecondary}
          onClick={() => onChange(offset + limit)}
          disabled={!hasNext}
        >
          Next
          <ChevronRightIcon className="h-3.5 w-3.5" />
        </button>
      </div>
    </nav>
  );
}
