import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import type { Prompt, Version, VersionListResponse } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useParams: () => ({ prompt_id: "p1" }),
  useSearchParams: () => new URLSearchParams(),
}));

let currentUserId = "owner";
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: { user_id: currentUserId, name: "Viewer", email: "v@example.com", created_at: "" },
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
  return {
    ...actual,
    getPrompt: vi.fn(),
    getVersions: vi.fn(),
    createVersion: vi.fn(),
    updatePromptMetadata: vi.fn(),
  };
});

import PromptDetailPage from "@/app/(app)/prompts/[prompt_id]/page";

const getPrompt = vi.mocked(api.getPrompt);
const getVersions = vi.mocked(api.getVersions);
const createVersion = vi.mocked(api.createVersion);

function v(n: number, over: Partial<Version> = {}): Version {
  return {
    version_id: `v${n}`,
    prompt_id: "p1",
    version_number: n,
    content: `content v${n}`,
    change_summary: n === 1 ? "Initial version." : `change ${n}`,
    created_by: "owner",
    created_at: "2026-01-0" + n + "T00:00:00Z",
    ...over,
  };
}

function prompt(over: Partial<Prompt> = {}): Prompt {
  const versions = [v(1), v(2)];
  return {
    prompt_id: "p1",
    user_id: "owner",
    title: "Academic Summarizer",
    description: "summarizes papers",
    purpose: "research",
    is_public: true,
    parent_prompt_id: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    owner: { user_id: "owner", name: "Owner Person" },
    versions,
    latest_version: versions[versions.length - 1],
    tags: [],
    ...over,
  };
}

const versionList = (items: Version[]): VersionListResponse => ({
  items,
  total: items.length,
});

beforeEach(() => {
  currentUserId = "owner";
  getPrompt.mockReset();
  getVersions.mockReset();
  createVersion.mockReset();
  getPrompt.mockResolvedValue(prompt());
  getVersions.mockResolvedValue(versionList([v(1), v(2)]));
});

describe("Prompt Detail", () => {
  it("5. shows a loading state while fetching", () => {
    getPrompt.mockReturnValue(new Promise(() => {})); // never resolves
    getVersions.mockReturnValue(new Promise(() => {}));
    render(<PromptDetailPage />);
    expect(screen.getByText(/loading prompt/i)).toBeInTheDocument();
  });

  it("6. handles a 404 (prompt not found / private)", async () => {
    getPrompt.mockRejectedValue(new api.ApiError(404, "not found", "Prompt not found."));
    getVersions.mockRejectedValue(new api.ApiError(404, "not found"));
    render(<PromptDetailPage />);
    expect(await screen.findByText(/prompt not found/i)).toBeInTheDocument();
  });

  it("11. renders version history with current version marked", async () => {
    render(<PromptDetailPage />);
    const history = await screen.findByRole("region", { name: /version history/i });
    expect(within(history).getByText("Version 1")).toBeInTheDocument();
    expect(within(history).getByText("Version 2")).toBeInTheDocument();
    expect(within(history).getByText("CURRENT")).toBeInTheDocument();
  });

  it("13. owner sees Edit Metadata and Create New Version controls", async () => {
    render(<PromptDetailPage />);
    expect(await screen.findByRole("button", { name: /edit metadata/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create new version/i })).toBeInTheDocument();
  });

  it("14. non-owner does NOT see owner-only write controls", async () => {
    currentUserId = "someone-else";
    render(<PromptDetailPage />);
    await screen.findByRole("heading", { name: /academic summarizer/i });
    expect(screen.queryByRole("button", { name: /edit metadata/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create new version/i })).not.toBeInTheDocument();
    expect(screen.getByText(/only the owner can edit/i)).toBeInTheDocument();
  });

  it("15. historical versions expose no edit/delete controls", async () => {
    const user = userEvent.setup();
    render(<PromptDetailPage />);
    const history = await screen.findByRole("region", { name: /version history/i });
    await user.click(within(history).getByRole("button", { name: /version 1/i }));
    const panel = screen.getByRole("region", { name: /version 1 details/i });
    expect(within(panel).getAllByText(/immutable/i).length).toBeGreaterThanOrEqual(1);
    // no mutation controls anywhere in a historical version panel
    expect(within(panel).queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button")).not.toBeInTheDocument();
    // content is shown as read-only text, never inside an input/textarea
    expect(within(panel).queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("12. Create Version submits ONLY content + change_summary", async () => {
    const user = userEvent.setup();
    createVersion.mockResolvedValue(v(3));
    render(<PromptDetailPage />);
    await user.click(await screen.findByRole("button", { name: /create new version/i }));
    const form = screen.getByRole("form", { name: /create new version/i });
    await user.type(within(form).getByLabelText(/new prompt content/i), "brand new content");
    await user.type(within(form).getByLabelText(/change summary/i), "tweaked wording");
    await user.click(within(form).getByRole("button", { name: /create version/i }));
    await waitFor(() => expect(createVersion).toHaveBeenCalledTimes(1));
    expect(createVersion).toHaveBeenCalledWith("p1", {
      content: "brand new content",
      change_summary: "tweaked wording",
    });
  });

  it("shows a lineage link when parent_prompt_id is present", async () => {
    getPrompt.mockImplementation(async (id: string) => {
      if (id === "p1") return prompt({ parent_prompt_id: "parent-1" });
      return prompt({ prompt_id: "parent-1", title: "Parent Prompt" });
    });
    render(<PromptDetailPage />);
    expect(await screen.findByRole("link", { name: /parent prompt/i })).toHaveAttribute(
      "href",
      "/prompts/parent-1",
    );
  });
});
