import { useId } from "react";

/**
 * Animated double helix, pure SVG + CSS (no animation library).
 *
 * Each rung is a horizontal bar with a dot at each end. A CSS keyframe scales
 * the rung on X through a full cosine-like cycle, and a staggered negative
 * animation-delay offsets every rung's phase — together that reads as a
 * rotating DNA strand. Decorative only (aria-hidden); motion is disabled by the
 * `prefers-reduced-motion` rule in globals.css.
 */
export function DnaHelix({
  rungs = 18,
  className = "",
}: {
  rungs?: number;
  className?: string;
}) {
  const uid = useId().replace(/:/g, "");
  const gradId = `helix-grad-${uid}`;
  const left = 22;
  const right = 138;
  const top = 18;
  const gap = 25;
  const height = top * 2 + gap * (rungs - 1);

  return (
    <svg
      aria-hidden
      focusable="false"
      viewBox={`0 0 160 ${height}`}
      className={`helix-float drop-shadow-[0_0_24px_rgba(139,92,246,0.55)] ${className}`}
    >
      <defs>
        <linearGradient id={gradId} gradientUnits="userSpaceOnUse" x1={left} x2={right} y1="0" y2="0">
          <stop offset="0" stopColor="#a78bfa" />
          <stop offset="0.5" stopColor="#6366f1" stopOpacity="0.55" />
          <stop offset="1" stopColor="#22d3ee" />
        </linearGradient>
      </defs>
      {Array.from({ length: rungs }, (_, i) => {
        const y = top + i * gap;
        return (
          <g
            key={i}
            className="helix-rung"
            style={{ animationDelay: `${-i * 0.4}s` }}
          >
            <line x1={left} x2={right} y1={y} y2={y} stroke={`url(#${gradId})`} strokeWidth="2.2" strokeLinecap="round" />
            <circle cx={left} cy={y} r="6.5" fill="#a78bfa" />
            <circle cx={right} cy={y} r="6.5" fill="#22d3ee" />
            <circle cx={left} cy={y} r="2.4" fill="#fff" opacity="0.85" />
            <circle cx={right} cy={y} r="2.4" fill="#fff" opacity="0.85" />
          </g>
        );
      })}
    </svg>
  );
}
