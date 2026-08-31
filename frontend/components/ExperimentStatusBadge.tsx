import type { ExperimentStatus } from "@/lib/types";

// Text label first (never colour-only).
export function ExperimentStatusBadge({ status }: { status: ExperimentStatus }) {
  const cls =
    status === "SUCCESS"
      ? "border-emerald-400 text-emerald-700 dark:border-emerald-700 dark:text-emerald-300"
      : status === "FAILED"
        ? "border-red-400 text-red-700 dark:border-red-700 dark:text-red-300"
        : "border-neutral-400 text-neutral-600 dark:border-neutral-600 dark:text-neutral-300";
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-semibold tracking-wide ${cls}`}
    >
      {status}
    </span>
  );
}
