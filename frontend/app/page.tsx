export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <div className="max-w-xl space-y-4">
        <p className="text-sm font-mono uppercase tracking-widest text-neutral-500">
          Phase 0 · Foundation
        </p>
        <h1 className="text-3xl font-semibold">PromptDNA</h1>
        <p className="text-neutral-600 dark:text-neutral-400">
          An intelligent knowledge database for prompt engineering and large
          language models. This is the development shell only — the application
          UI is not built yet.
        </p>
        <p className="text-sm text-neutral-500">
          Backend API base URL:{" "}
          <code className="font-mono">
            {process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}
          </code>
        </p>
      </div>
    </main>
  );
}
