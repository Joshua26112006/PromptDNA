"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import {
  ArrowRightIcon,
  BeakerIcon,
  BranchIcon,
  CheckCircleIcon,
  LayersIcon,
  LockIcon,
  SearchIcon,
  SparklesIcon,
} from "@/components/icons";
import { DnaHelix } from "@/components/landing/DnaHelix";
import { LineageDemo } from "@/components/landing/LineageDemo";
import { Reveal } from "@/components/landing/Reveal";
import { Wordmark } from "@/components/Wordmark";
import { buttonGhost, buttonPrimary, buttonSecondary, focusRing } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";

const FEATURES = [
  {
    icon: LayersIcon,
    title: "Immutable version history",
    body: "Every edit becomes a new, permanent version. Compare how a prompt evolved and never lose a wording that worked.",
  },
  {
    icon: BeakerIcon,
    title: "Experiments on real models",
    body: "Run any version against a model, keep the output and latency, and score it — so improvements are measured, not guessed.",
  },
  {
    icon: SearchIcon,
    title: "Semantic search",
    body: "Find prompts by what they mean using pgvector similarity, alongside fast keyword search.",
  },
  {
    icon: BranchIcon,
    title: "Lineage knowledge graph",
    body: "See which prompts were derived from which, with variable-depth ancestor and descendant traversal in Neo4j.",
  },
  {
    icon: LockIcon,
    title: "Private by default",
    body: "JWT authentication with Argon2 hashing. Other people's private prompts are never visible to you.",
  },
  {
    icon: SparklesIcon,
    title: "Local or cloud models",
    body: "Plug in OpenAI-compatible providers or run open models like Gemma and Qwen locally through Ollama.",
  },
];

const STACK = [
  {
    name: "PostgreSQL",
    role: "System of record",
    body: "Nine normalized tables (3NF) hold users, prompts, versions, models and experiments, with constraints doing the policing.",
    color: "from-sky-400 to-indigo-500",
  },
  {
    name: "pgvector",
    role: "Meaning, as vectors",
    body: "1536-dimension embeddings live inside Postgres and are searched by cosine distance with an HNSW index.",
    color: "from-violet-400 to-fuchsia-500",
  },
  {
    name: "Neo4j",
    role: "Lineage graph",
    body: "A derived projection of prompt relationships for variable-depth traversal. It can be rebuilt from Postgres at any time.",
    color: "from-cyan-300 to-emerald-400",
  },
];

const STATS = [
  { value: "9", label: "normalized tables" },
  { value: "1536", label: "dimensional embeddings" },
  { value: "3NF", label: "relational design" },
  { value: "∞", label: "versions, never overwritten" },
];

function GradientCta({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className={`${buttonPrimary} h-11 px-6 text-[15px]`}>
      {children}
    </Link>
  );
}

/** Public landing page. Signed-in users go straight to the Prompt Library. */
export default function Home() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") router.replace("/prompts");
  }, [status, router]);

  return (
    <div className="relative flex flex-1 flex-col">
      {/* ------------------------------ nav ------------------------------ */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-surface/50 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-5 sm:px-8">
          <Link href="/" aria-label="PromptDNA home" className={`rounded-lg ${focusRing}`}>
            <Wordmark />
          </Link>
          <nav aria-label="Sections" className="ml-6 hidden items-center gap-1 md:flex">
            {[
              ["#features", "Features"],
              ["#architecture", "Architecture"],
              ["#lineage", "Lineage"],
            ].map(([href, label]) => (
              <a key={href} href={href} className={`${buttonGhost} !h-8`}>
                {label}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Link href="/login" className={`${buttonGhost} hidden sm:inline-flex`}>
              Sign in
            </Link>
            <Link href="/register" className={`${buttonPrimary} !h-9`}>
              Get started
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* ------------------------------ hero ----------------------------- */}
        <section className="relative mx-auto grid max-w-6xl items-center gap-10 px-5 pb-20 pt-16 sm:px-8 lg:grid-cols-[1.15fr_0.85fr] lg:pb-28 lg:pt-24">
          <div>
            <Reveal>
              <span className="glass inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-medium text-accent-ink">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_10px_2px_rgba(52,211,153,0.7)]" />
                PostgreSQL · pgvector · Neo4j — one coherent system
              </span>
            </Reveal>

            <Reveal delay={80}>
              <h1 className="mt-6 text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
                <span className="text-gradient">The DNA of every prompt you write.</span>
              </h1>
            </Reveal>

            <Reveal delay={160}>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-muted">
                PromptDNA is an intelligent knowledge database for prompt engineering. Version
                every change, test prompts against real models, search by meaning, and trace
                exactly how each prompt evolved.
              </p>
            </Reveal>

            <Reveal delay={240}>
              <div className="mt-9 flex flex-wrap items-center gap-3">
                <GradientCta href="/register">
                  Start building <ArrowRightIcon className="h-4 w-4" />
                </GradientCta>
                <Link href="/login" className={`${buttonSecondary} h-11 px-6 text-[15px]`}>
                  Sign in
                </Link>
              </div>
            </Reveal>

            <Reveal delay={320}>
              <ul className="mt-9 flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink-muted">
                {["Immutable versions", "Real model experiments", "Semantic + graph search"].map((t) => (
                  <li key={t} className="inline-flex items-center gap-1.5">
                    <CheckCircleIcon className="h-4 w-4 text-emerald-400" />
                    {t}
                  </li>
                ))}
              </ul>
            </Reveal>
          </div>

          {/* hero visual: helix + floating glass cards */}
          <Reveal delay={200} className="relative mx-auto h-[26rem] w-full max-w-sm lg:h-[34rem]">
            <div aria-hidden className="absolute inset-x-8 top-1/2 h-72 -translate-y-1/2 rounded-full bg-violet-600/30 blur-[90px]" />
            <DnaHelix className="relative mx-auto h-full w-auto" />

            <div className="glass glow-border absolute -left-2 top-10 rounded-2xl px-4 py-3 text-sm sm:-left-10">
              <p className="text-[11px] uppercase tracking-wider text-ink-subtle">Version</p>
              <p className="mt-0.5 font-medium">v3 · structured summary</p>
            </div>
            <div className="glass absolute -right-2 top-1/2 rounded-2xl px-4 py-3 text-sm sm:-right-8">
              <p className="text-[11px] uppercase tracking-wider text-ink-subtle">Experiment</p>
              <p className="mt-0.5 flex items-center gap-2 font-medium">
                <span className="h-2 w-2 rounded-full bg-emerald-400" /> Success · scored
              </p>
            </div>
            <div className="glass absolute bottom-8 left-0 rounded-2xl px-4 py-3 text-sm sm:-left-6">
              <p className="text-[11px] uppercase tracking-wider text-ink-subtle">Lineage</p>
              <p className="mt-0.5 font-mono text-xs text-cyan-300">DERIVED_FROM</p>
            </div>
          </Reveal>
        </section>

        {/* ------------------------------ stats ---------------------------- */}
        <section aria-label="At a glance" className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal>
            <dl className="glass grid grid-cols-2 gap-px overflow-hidden rounded-2xl sm:grid-cols-4">
              {STATS.map((s) => (
                <div key={s.label} className="bg-surface/40 px-6 py-6 text-center">
                  <dt className="sr-only">{s.label}</dt>
                  <dd className="text-3xl font-semibold tracking-tight text-gradient">{s.value}</dd>
                  <p className="mt-1 text-xs text-ink-muted">{s.label}</p>
                </div>
              ))}
            </dl>
          </Reveal>
        </section>

        {/* ---------------------------- features --------------------------- */}
        <section id="features" className="mx-auto max-w-6xl scroll-mt-24 px-5 py-24 sm:px-8">
          <Reveal>
            <p className="text-sm font-medium uppercase tracking-widest text-accent">Features</p>
            <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
              Everything you need to treat prompts like real engineering artifacts.
            </h2>
          </Reveal>
          <ul className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => (
              <li key={f.title}>
                <Reveal delay={i * 70} className="h-full">
                  <div className="glass group h-full rounded-2xl p-6 transition duration-300 hover:-translate-y-1 hover:border-accent-line hover:shadow-[0_0_0_1px_rgba(124,58,237,0.4),0_24px_60px_-20px_rgba(124,58,237,0.55)]">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/30 to-cyan-400/20 text-accent-ink ring-1 ring-accent-line transition group-hover:scale-110">
                      <f.icon className="h-5 w-5" />
                    </span>
                    <h3 className="mt-5 text-lg font-semibold tracking-tight">{f.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-ink-muted">{f.body}</p>
                  </div>
                </Reveal>
              </li>
            ))}
          </ul>
        </section>

        {/* -------------------------- architecture ------------------------- */}
        <section id="architecture" className="mx-auto max-w-6xl scroll-mt-24 px-5 pb-24 sm:px-8">
          <Reveal>
            <p className="text-sm font-medium uppercase tracking-widest text-accent">Architecture</p>
            <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
              Three databases, one source of truth.
            </h2>
            <p className="mt-4 max-w-2xl text-ink-muted">
              PostgreSQL is authoritative. Vectors and graph relationships are derived from it, so
              each store does the one job it is best at.
            </p>
          </Reveal>
          <ol className="mt-12 grid gap-5 lg:grid-cols-3">
            {STACK.map((s, i) => (
              <li key={s.name}>
                <Reveal delay={i * 100} className="h-full">
                  <div className="glass glow-border relative h-full rounded-2xl p-7">
                    <span className={`inline-block rounded-lg bg-gradient-to-r ${s.color} px-3 py-1 text-sm font-semibold text-black`}>
                      {s.name}
                    </span>
                    <p className="mt-4 text-xs font-medium uppercase tracking-widest text-ink-subtle">
                      {s.role}
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-ink-muted">{s.body}</p>
                    <span aria-hidden className="absolute right-6 top-6 font-mono text-4xl font-bold text-white/5">
                      0{i + 1}
                    </span>
                  </div>
                </Reveal>
              </li>
            ))}
          </ol>
        </section>

        {/* ----------------------------- lineage --------------------------- */}
        <section id="lineage" className="mx-auto max-w-6xl scroll-mt-24 px-5 pb-24 sm:px-8">
          <div className="glass glow-border relative grid items-center gap-8 rounded-3xl p-8 sm:p-12 lg:grid-cols-2">
            <Reveal>
              <p className="text-sm font-medium uppercase tracking-widest text-accent">Lineage</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                See how every prompt grew from another.
              </h2>
              <p className="mt-4 text-ink-muted">
                Derive a new prompt from an existing one and PromptDNA records the relationship in
                PostgreSQL, then projects it into the graph. Walk ancestors, descendants and
                related prompts at any depth.
              </p>
            </Reveal>
            <Reveal delay={120}>
              <LineageDemo className="mx-auto w-full max-w-md" />
            </Reveal>
          </div>
        </section>

        {/* ------------------------------- cta ----------------------------- */}
        <section className="mx-auto max-w-4xl px-5 pb-28 text-center sm:px-8">
          <Reveal>
            <h2 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              <span className="text-gradient">Start treating prompts like code.</span>
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-ink-muted">
              Create an account, add your first prompt, and watch its history grow.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <GradientCta href="/register">
                Create your account <ArrowRightIcon className="h-4 w-4" />
              </GradientCta>
              <Link href="/login" className={`${buttonSecondary} h-11 px-6 text-[15px]`}>
                Sign in
              </Link>
            </div>
          </Reveal>
        </section>
      </main>

      <footer className="border-t border-white/5 bg-surface/40 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-6 text-xs text-ink-subtle sm:px-8">
          <Wordmark />
          <span>Prompt lineage, experiments and retrieval · PostgreSQL · pgvector · Neo4j</span>
        </div>
      </footer>
    </div>
  );
}
