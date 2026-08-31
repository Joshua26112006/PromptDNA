import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import type { PromptListResponse } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: { user_id: "u1", name: "Alice", email: "a@example.com", created_at: "" },
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
  return { ...actual, listPrompts: vi.fn() };
});

import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";
import NewPromptPage from "@/app/(app)/prompts/new/page";
import PromptLibraryPage from "@/app/(app)/prompts/page";

const listPrompts = vi.mocked(api.listPrompts);

function page(overrides: Partial<PromptListResponse> = {}): PromptListResponse {
  return {
    items: [
      {
        prompt_id: "p1",
        user_id: "u1",
        title: "SQL Optimizer",
        description: "makes queries fast",
        purpose: null,
        is_public: false,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-02T00:00:00Z",
        latest_version_number: 3,
      },
      {
        prompt_id: "p2",
        user_id: "u9",
        title: "Public Helper",
        description: null,
        purpose: null,
        is_public: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-02T00:00:00Z",
        latest_version_number: 1,
      },
    ],
    limit: 20,
    offset: 0,
    total: 42,
    ...overrides,
  };
}

beforeEach(() => {
  listPrompts.mockReset();
  listPrompts.mockResolvedValue(page());
});

describe("auth pages render", () => {
  it("1. login page renders", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: /log in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("2. register page renders", () => {
    render(<RegisterPage />);
    expect(screen.getByRole("heading", { name: /create your account/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
  });
});

describe("Prompt Library", () => {
  it("3. prompts page renders with header and New Prompt CTA", async () => {
    render(<PromptLibraryPage />);
    expect(screen.getByRole("heading", { name: /prompt library/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /new prompt/i })).toHaveAttribute("href", "/prompts/new");
    await waitFor(() => expect(listPrompts).toHaveBeenCalled());
  });

  it("4. new prompt page renders", () => {
    render(<NewPromptPage />);
    expect(screen.getByRole("heading", { name: /new prompt/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/prompt content/i)).toBeInTheDocument();
  });

  it("8. displays returned prompts", async () => {
    render(<PromptLibraryPage />);
    expect(await screen.findByText("SQL Optimizer")).toBeInTheDocument();
    expect(screen.getByText("Public Helper")).toBeInTheDocument();
    // visibility labels are text, not colour-only
    expect(screen.getAllByText("PRIVATE").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("PUBLIC")).toBeInTheDocument();
  });

  it("9. search sends the search parameter to the backend", async () => {
    const user = userEvent.setup();
    render(<PromptLibraryPage />);
    await waitFor(() => expect(listPrompts).toHaveBeenCalled());
    await user.type(screen.getByRole("searchbox"), "optimizer");
    await user.click(screen.getByRole("button", { name: /^search$/i }));
    await waitFor(() =>
      expect(listPrompts).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "optimizer", offset: 0 }),
      ),
    );
  });

  it("10. pagination Next changes offset", async () => {
    const user = userEvent.setup();
    listPrompts.mockResolvedValue(page({ total: 50 })); // more pages exist
    render(<PromptLibraryPage />);
    await screen.findByText("SQL Optimizer");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() =>
      expect(listPrompts).toHaveBeenLastCalledWith(
        expect.objectContaining({ offset: 20 }),
      ),
    );
  });

  it("visibility filter sends is_public", async () => {
    const user = userEvent.setup();
    render(<PromptLibraryPage />);
    await waitFor(() => expect(listPrompts).toHaveBeenCalled());
    await user.selectOptions(screen.getByLabelText(/visibility/i), "public");
    await waitFor(() =>
      expect(listPrompts).toHaveBeenLastCalledWith(
        expect.objectContaining({ isPublic: true }),
      ),
    );
  });
});
