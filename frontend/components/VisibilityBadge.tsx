// Public / private indicator. Text label first (never colour-only); the icon
// is decorative and hidden from assistive tech.

import { GlobeIcon, LockIcon } from "./icons";

export function VisibilityBadge({ isPublic }: { isPublic: boolean }) {
  const label = isPublic ? "PUBLIC" : "PRIVATE";
  const cls = isPublic
    ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-300"
    : "border-neutral-200 bg-neutral-100 text-neutral-600 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300";
  const Icon = isPublic ? GlobeIcon : LockIcon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold tracking-wide ${cls}`}
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}
