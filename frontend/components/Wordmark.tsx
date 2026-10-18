import { LogoMark } from "./icons";

/**
 * PromptDNA lockup: the strand mark in a brand tile beside the wordmark.
 * "DNA" is weighted to reinforce the lineage idea without a second colour.
 */
export function Wordmark({ size = "sm" }: { size?: "sm" | "lg" }) {
  const lg = size === "lg";
  return (
    <span className="inline-flex items-center gap-2.5">
      <span
        aria-hidden
        className={`flex items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-indigo-500 to-cyan-400 text-white shadow-[0_0_22px_-4px_rgba(139,92,246,0.9)] ${
          lg ? "h-10 w-10" : "h-7 w-7"
        }`}
      >
        <LogoMark className={lg ? "h-6 w-6" : "h-4 w-4"} />
      </span>
      <span
        className={`font-semibold tracking-tight text-ink ${lg ? "text-xl" : "text-[15px]"}`}
      >
        Prompt<span className="bg-gradient-to-r from-violet-300 to-cyan-300 bg-clip-text text-transparent">DNA</span>
      </span>
    </span>
  );
}
