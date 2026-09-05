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
  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));
  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  return (
    <nav
      className="flex items-center justify-between gap-3 pt-1 text-sm"
      aria-label="Pagination"
    >
      <button
        type="button"
        className={buttonSecondary}
        onClick={() => onChange(Math.max(0, offset - limit))}
        disabled={!hasPrev}
      >
        <ChevronLeftIcon className="h-3.5 w-3.5" />
        Previous
      </button>
      <span className="text-neutral-500 dark:text-neutral-400" aria-live="polite">
        Page {page} of {pageCount}
        <span className="ml-2 text-neutral-400 dark:text-neutral-600">({total} total)</span>
      </span>
      <button
        type="button"
        className={buttonSecondary}
        onClick={() => onChange(offset + limit)}
        disabled={!hasNext}
      >
        Next
        <ChevronRightIcon className="h-3.5 w-3.5" />
      </button>
    </nav>
  );
}
