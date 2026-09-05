import type { ExperimentStatus } from "@/lib/types";

import { CheckCircleIcon, ClockIcon, XCircleIcon } from "./icons";

// Text label first (never colour-only).
export function ExperimentStatusBadge({ status }: { status: ExperimentStatus }) {
  const cls =
    status === "SUCCESS"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-300"
      : status === "FAILED"
        ? "border-red-200 bg-red-50 text-red-700 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-300"
        : "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-300";
  const Icon =
    status === "SUCCESS" ? CheckCircleIcon : status === "FAILED" ? XCircleIcon : ClockIcon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold tracking-wide ${cls}`}
    >
      <Icon className="h-3 w-3" />
      {status}
    </span>
  );
}
