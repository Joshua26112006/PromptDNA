import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace, refresh: vi.fn() }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (orig) => {
  const actual = await orig<typeof import("@/lib/api")>();
  return {
    ...actual,
    createPrompt: vi.fn(),
    getCurrentUser: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
  };
});

// --- 7. Prompt creation sends the correct payload ---------------------------

describe("Create Prompt form", () => {
  it("7. POSTs title/content/description/purpose/is_public and NOT ownership fields", async () => {
    const NewPromptPage = (await import("@/app/(app)/prompts/new/page")).default;
    // this page uses useAuth via ProtectedShell's siblings? no — it only uses router + api
    const createPrompt = vi.mocked(api.createPrompt);
    createPrompt.mockResolvedValue({
      prompt_id: "new-1",
      user_id: "u1",
      title: "T",
      description: null,
      purpose: null,
      is_public: false,
      parent_prompt_id: null,
      created_at: "",
      updated_at: "",
      owner: { user_id: "u1", name: "A" },
      versions: [],
      latest_version: null,
      tags: [],
    });

    const user = userEvent.setup();
    render(<NewPromptPage />);

    await user.type(screen.getByLabelText(/title/i), "Summarizer");
    await user.type(screen.getByLabelText(/description/i), "d");
    await user.type(screen.getByLabelText(/purpose/i), "p");
    await user.type(screen.getByLabelText(/prompt content/i), "You are helpful.");
    await user.click(screen.getByLabelText(/public/i));
    await user.click(screen.getByRole("button", { name: /create prompt/i }));

    await waitFor(() => expect(createPrompt).toHaveBeenCalledTimes(1));
    const payload = createPrompt.mock.calls[0][0];
    expect(payload).toEqual({
      title: "Summarizer",
      content: "You are helpful.",
      description: "d",
      purpose: "p",
      is_public: true,
    });
    expect(payload).not.toHaveProperty("user_id");
    expect(payload).not.toHaveProperty("version_number");
    expect(payload).not.toHaveProperty("created_by");
    expect(replace).not.toHaveBeenCalled(); // uses router.push, not replace
  });
});

// --- 16. Logout clears authentication state -------------------------------

describe("Auth context logout", () => {
  beforeEach(() => {
    window.localStorage.setItem("promptdna.access_token", "a-token");
    vi.mocked(api.getCurrentUser).mockResolvedValue({
      user_id: "u1",
      name: "Alice",
      email: "alice@example.com",
      created_at: "2026-01-01T00:00:00Z",
    });
  });

  it("16. removes the token and marks the user unauthenticated", async () => {
    const { AuthProvider, useAuth } = await import("@/lib/auth-context");

    function Probe() {
      const { status, user, logout } = useAuth();
      return (
        <div>
          <span data-testid="status">{status}</span>
          <span data-testid="user">{user?.name ?? "none"}</span>
          <button onClick={logout}>Log out</button>
        </div>
      );
    }

    const user = userEvent.setup();
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    // resolves the stored token to a user on mount
    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated"),
    );
    expect(screen.getByTestId("user")).toHaveTextContent("Alice");

    await user.click(screen.getByRole("button", { name: /log out/i }));

    expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    expect(screen.getByTestId("user")).toHaveTextContent("none");
    expect(window.localStorage.getItem("promptdna.access_token")).toBeNull();
    expect(replace).toHaveBeenCalledWith("/login");
  });
});
