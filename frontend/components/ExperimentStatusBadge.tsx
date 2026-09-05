import type { ExperimentStatus } from "@/lib/types";

import { CheckCircleIcon, ClockIcon, XCircleIcon } from "./icons";

const STYLES: Record<ExperimentStatus, string> = {
  SUCCESS: "border-ok-line bg-ok-soft text-ok",
  FAILED: "border-danger-line bg-danger-soft text-danger",
  PENDING: "border-warn-line bg-warn-soft text-warn",
};

const ICONS: Record<ExperimentStatus, typeof CheckCircleIcon> = {
  SUCCESS: CheckCircleIcon,
  FAILED: XCircleIcon,
  PENDING: ClockIcon,
};

// Text label first (never colour-only).
export function ExperimentStatusBadge({ status }: { status: ExperimentStatus }) {
  const Icon = ICONS[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${STYLES[status]}`}
    >
      <Icon className="h-3 w-3" />
      {status}
    </span>
  );
}
