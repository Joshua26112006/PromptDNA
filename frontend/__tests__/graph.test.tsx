import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import type { GraphResponse } from "@/lib/types";

vi.mock("@/lib/api", async (orig) => {
  const actual = await orig<typeof import("@/lib/api")>();
  return { ...actual, getPromptGraph: vi.fn() };
});

import { GraphSection } from "@/components/GraphSection";

const getPromptGraph = vi.mocked(api.getPromptGraph);

const related: GraphResponse = {
  prompt_id: "p1",
  title: "Derived Summarizer",
  kind: "related",
  relationships: [
    {
      type: "DERIVED_FROM",
      direction: "outgoing",
      prompt_id: "root",
      title: "Research Summarizer V2",
      depth: 1,
      rel_types: null,
    },
    {
      type: "FORKED_FROM",
      direction: "incoming",
      prompt_id: "fork",
      title: "A Fork",
      depth: 1,
      rel_types: null,
    },
  ],
};

const ancestors: GraphResponse = {
  prompt_id: "p1",
  title: "Derived Summarizer",
  kind: "ancestors",
  relationships: [
    {
      type: null,
      direction: null,
      prompt_id: "root",
      title: "Research Summarizer V2",
      depth: 1,
      rel_types: ["DERIVED_FROM"],
    },
  ],
};

beforeEach(() => {
  getPromptGraph.mockReset();
  getPromptGraph.mockImplementation(async (_id, kind) =>
    kind === "related" ? related : ancestors,
  );
});

describe("GraphSection (knowledge graph)", () => {
  it("renders the Prompt Relationships section and the graph-vs-semantic note", async () => {
    render(<GraphSection promptId="p1" />);
    expect(
      screen.getByRole("region", { name: /prompt relationships/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/different from semantic search/i)).toBeInTheDocument();
    await waitFor(() => expect(getPromptGraph).toHaveBeenCalled());
  });

  it("requests both ancestors and related from the graph API", async () => {
    render(<GraphSection promptId="p1" />);
    await waitFor(() => expect(getPromptGraph).toHaveBeenCalledTimes(2));
    expect(getPromptGraph).toHaveBeenCalledWith("p1", "related");
    expect(getPromptGraph).toHaveBeenCalledWith("p1", "ancestors");
  });

  it("shows connected prompts with relationship type/direction and links to them", async () => {
    render(<GraphSection promptId="p1" />);
    const region = await screen.findByRole("region", { name: /prompt relationships/i });
    const rootLinks = within(region).getAllByRole("link", {
      name: /research summarizer v2/i,
    });
    expect(rootLinks.length).toBeGreaterThanOrEqual(1);
    expect(rootLinks.every((a) => a.getAttribute("href") === "/prompts/root")).toBe(true);
    expect(within(region).getAllByText(/derived from/i).length).toBeGreaterThanOrEqual(1);
    expect(within(region).getByRole("link", { name: /a fork/i })).toHaveAttribute(
      "href",
      "/prompts/fork",
    );
  });

  it("shows 'Graph relationships unavailable' when the API fails (e.g. 503)", async () => {
    getPromptGraph.mockRejectedValue(
      new api.ApiError(503, "unavailable", "The knowledge graph is not enabled."),
    );
    render(<GraphSection promptId="p1" />);
    expect(
      await screen.findByText(/graph relationships unavailable/i),
    ).toBeInTheDocument();
  });

  it("shows a loading state first", () => {
    getPromptGraph.mockReturnValue(new Promise(() => {}));
    render(<GraphSection promptId="p1" />);
    expect(screen.getByText(/loading graph/i)).toBeInTheDocument();
  });
});
