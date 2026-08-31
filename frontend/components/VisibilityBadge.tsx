// Public / private indicator. Text label first (never colour-only); the icon
// is decorative and hidden from assistive tech.

export function VisibilityBadge({ isPublic }: { isPublic: boolean }) {
  const label = isPublic ? "PUBLIC" : "PRIVATE";
  const cls = isPublic
    ? "border-emerald-400 text-emerald-700 dark:border-emerald-700 dark:text-emerald-300"
    : "border-neutral-400 text-neutral-600 dark:border-neutral-600 dark:text-neutral-300";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] font-semibold tracking-wide ${cls}`}
    >
      <span aria-hidden>{isPublic ? "🌐" : "🔒"}</span>
      {label}
    </span>
  );
}
