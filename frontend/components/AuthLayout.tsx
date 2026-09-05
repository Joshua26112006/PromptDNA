import type { ReactNode } from "react";

import { BranchIcon, LayersIcon, SparklesIcon } from "./icons";
import { Wordmark } from "./Wordmark";

const PILLARS = [
  {
    icon: LayersIcon,
    title: "Version every change",
    body: "Each edit becomes an immutable version, so you can always see what a prompt used to be.",
  },
  {
    icon: SparklesIcon,
    title: "Search by meaning",
    body: "Find prompts by what they do — not only by the words they happen to contain.",
  },
  {
    icon: BranchIcon,
    title: "Follow the lineage",
    body: "See which prompts were derived from which, and how a family of prompts evolved.",
  },
];

/**
 * Two-pane authentication frame: product story on the left (desktop only),
 * the form on the right. Gives a first-time visitor context for what they are
 * signing in to instead of a bare form on a page.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex flex-1 flex-col lg:grid lg:grid-cols-[1.05fr_1fr]">
      {/* Story pane */}
      <section
        aria-label="About PromptDNA"
        className="relative hidden overflow-hidden border-r border-line bg-panel px-10 py-12 lg:flex lg:flex-col lg:justify-center"
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.55] [background-image:radial-gradient(circle_at_1px_1px,var(--line-strong)_1px,transparent_0)] [background-size:22px_22px]"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -left-24 top-1/4 h-72 w-72 rounded-full bg-accent-soft blur-3xl"
        />

        <div className="relative max-w-md">
          <Wordmark size="lg" />
          <h2 className="mt-8 text-3xl font-semibold leading-tight tracking-tight text-ink">
            A knowledge base for the prompts you actually rely on.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-muted">
            PromptDNA keeps the full history of a prompt — every version, every
            experiment against a model, and every relationship to the prompts it
            grew out of.
          </p>

          <ul className="mt-9 space-y-5">
            {PILLARS.map((p) => (
              <li key={p.title} className="flex gap-3.5">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-accent-line bg-accent-soft text-accent">
                  <p.icon className="h-4 w-4" />
                </span>
                <span>
                  <span className="block text-sm font-medium text-ink">{p.title}</span>
                  <span className="mt-0.5 block text-sm leading-relaxed text-ink-muted">{p.body}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Form pane */}
      <section className="flex flex-1 items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Wordmark size="lg" />
          </div>
          {children}
        </div>
      </section>
    </main>
  );
}
