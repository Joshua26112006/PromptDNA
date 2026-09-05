// Public / private indicator. The text label carries the meaning (never
// colour-only); the icon is decorative.

import { GlobeIcon, LockIcon } from "./icons";

export function VisibilityBadge({ isPublic }: { isPublic: boolean }) {
  const Icon = isPublic ? GlobeIcon : LockIcon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
        isPublic
          ? "border-ok-line bg-ok-soft text-ok"
          : "border-line bg-panel-muted text-ink-muted"
      }`}
    >
      <Icon className="h-3 w-3" />
      {isPublic ? "PUBLIC" : "PRIVATE"}
    </span>
  );
}
