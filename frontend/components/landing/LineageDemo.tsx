/**
 * Illustrative lineage graph (decorative): three prompts connected by animated
 * DERIVED_FROM edges, in the same shape the real Knowledge Graph section shows.
 */
const NODES = [
  { x: 110, y: 52, label: "Academic Research Paper Summarizer", sub: "root prompt · 3 versions", tone: "violet" },
  { x: 250, y: 168, label: "Research Article Analyzer", sub: "derived from the summarizer", tone: "cyan" },
  { x: 110, y: 284, label: "Literature Review Assistant", sub: "derived from the analyzer", tone: "pink" },
] as const;

const TONES = {
  violet: { stroke: "#a78bfa", fill: "rgba(124,58,237,0.18)" },
  cyan: { stroke: "#22d3ee", fill: "rgba(34,211,238,0.14)" },
  pink: { stroke: "#f472b6", fill: "rgba(244,114,182,0.14)" },
} as const;

export function LineageDemo({ className = "" }: { className?: string }) {
  return (
    <svg
      role="img"
      aria-label="Example lineage: Literature Review Assistant derived from Research Article Analyzer, derived from Academic Research Paper Summarizer"
      viewBox="0 0 400 336"
      className={className}
    >
      {/* edges (child -> parent) */}
      <path className="edge-flow" d="M250 168 C 250 118, 110 118, 110 84" fill="none" stroke="#22d3ee" strokeWidth="2" strokeLinecap="round" />
      <path className="edge-flow" d="M110 284 C 110 234, 250 234, 250 200" fill="none" stroke="#f472b6" strokeWidth="2" strokeLinecap="round" />
      <text x="205" y="126" fontSize="9.5" fill="#9aa3d6" letterSpacing="1.4" className="font-mono">DERIVED_FROM</text>
      <text x="55" y="242" fontSize="9.5" fill="#9aa3d6" letterSpacing="1.4" className="font-mono">DERIVED_FROM</text>

      {NODES.map((n, i) => {
        const t = TONES[n.tone];
        return (
          <g key={n.label}>
            <circle className="node-pulse" cx={n.x} cy={n.y} r="34" fill={t.fill} style={{ animationDelay: `${i * 0.6}s` }} />
            <circle cx={n.x} cy={n.y} r="22" fill="#0d1021" stroke={t.stroke} strokeWidth="2" />
            <circle cx={n.x} cy={n.y} r="6" fill={t.stroke} />
            <text x={n.x + (n.x < 200 ? 40 : -40)} y={n.y - 2} fontSize="12.5" fontWeight="600" fill="#eef0ff" textAnchor={n.x < 200 ? "start" : "end"}>
              {n.label.length > 24 ? n.label.slice(0, n.label.lastIndexOf(" ", 24)) : n.label}
            </text>
            {n.label.length > 24 && (
              <text x={n.x + (n.x < 200 ? 40 : -40)} y={n.y + 13} fontSize="12.5" fontWeight="600" fill="#eef0ff" textAnchor={n.x < 200 ? "start" : "end"}>
                {n.label.slice(n.label.lastIndexOf(" ", 24) + 1)}
              </text>
            )}
            <text x={n.x + (n.x < 200 ? 40 : -40)} y={n.y + (n.label.length > 24 ? 29 : 15)} fontSize="10" fill="#8a92c4" textAnchor={n.x < 200 ? "start" : "end"}>
              {n.sub}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
