import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import type { SemanticSearchResult } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: { user_id: "u1", name: "A", email: "a@example.com", created_at: "" },
    status: "authenticated",
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/lib/api", async (orig) => {
  const actual = await orig<typeof import("@/lib/api")>();
  return { ...actual, listPrompts: vi.fn(), semanticSearch: vi.fn() };
});

import PromptLibraryPage from "@/app/(app)/prompts/page";

const listPrompts = vi.mocked(api.listPrompts);
const semanticSearch = vi.mocked(api.semanticSearch);

const results: SemanticSearchResult[] = [
  {
    prompt_id: "p1",
    version_id: "v1",
    prompt_title: "Academic Summarizer",
    version_number: 3,
    content_preview: "Summarize academic research papers…",
    similarity: 0.87,
    is_public: true,
    created_at: "2026-01-01T00:00:00Z",
  },
];

beforeEach(() => {
  listPrompts.mockReset();
  semanticSearch.mockReset();
  listPrompts.mockResolvedValue({ items: [], limit: 20, offset: 0, total: 0 });
  semanticSearch.mockResolvedValue({ query: "x", count: 1, results });
});

describe("Prompt Library — semantic search", () => {
  it("shows a search-mode selector (Search by text / Semantic Search)", async () => {
    render(<PromptLibraryPage />);
    expect(await screen.findByRole("radio", { name: /search by text/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /semantic search/i })).toBeInTheDocument();
  });

  it("lexical mode still calls listPrompts", async () => {
    render(<PromptLibraryPage />);
    await waitFor(() => expect(listPrompts).toHaveBeenCalled());
    expect(semanticSearch).not.toHaveBeenCalled();
  });

  it("semantic mode sends the query to the semantic endpoint", async () => {
    const user = userEvent.setup();
    render(<PromptLibraryPage />);
    await user.click(screen.getByRole("radio", { name: /semantic search/i }));
    await user.type(
      screen.getByLabelText(/describe what you're looking for/i),
      "help me summarize scholarly articles",
    );
    await user.click(screen.getByRole("button", { name: /search/i }));
    await waitFor(() => expect(semanticSearch).toHaveBeenCalledTimes(1));
    expect(semanticSearch).toHaveBeenCalledWith(
      "help me summarize scholarly articles",
      expect.objectContaining({ limit: expect.any(Number) }),
    );
  });

  it("renders semantic results with similarity and links to the prompt", async () => {
    const user = userEvent.setup();
    render(<PromptLibraryPage />);
    await user.click(screen.getByRole("radio", { name: /semantic search/i }));
    await user.type(screen.getByLabelText(/describe what/i), "summaries");
    await user.click(screen.getByRole("button", { name: /search/i }));

    const region = await screen.findByRole("region", { name: /semantic search results/i });
    expect(within(region).getByText("Academic Summarizer")).toBeInTheDocument();
    expect(within(region).getByText(/similarity 0\.870/)).toBeInTheDocument();
    expect(within(region).getByRole("link", { name: /academic summarizer/i })).toHaveAttribute(
      "href",
      "/prompts/p1",
    );
  });

  it("shows a loading state and then an empty state", async () => {
    const user = userEvent.setup();
    let resolve!: (v: { query: string; count: number; results: SemanticSearchResult[] }) => void;
    semanticSearch.mockReturnValue(new Promise((r) => (resolve = r)));
    render(<PromptLibraryPage />);
    await user.click(screen.getByRole("radio", { name: /semantic search/i }));
    await user.type(screen.getByLabelText(/describe what/i), "q");
    await user.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByText(/searching/i)).toBeInTheDocument();
    resolve({ query: "q", count: 0, results: [] });
    expect(await screen.findByText(/no semantically similar prompts/i)).toBeInTheDocument();
  });

  it("shows an error (e.g. semantic search unavailable) without crashing", async () => {
    const user = userEvent.setup();
    semanticSearch.mockRejectedValue(new api.ApiError(503, "unavailable", "Semantic search is not available on this deployment."));
    render(<PromptLibraryPage />);
    await user.click(screen.getByRole("radio", { name: /semantic search/i }));
    await user.type(screen.getByLabelText(/describe what/i), "q");
    await user.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
