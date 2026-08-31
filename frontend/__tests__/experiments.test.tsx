import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import type { Experiment, Model } from "@/lib/types";

vi.mock("@/lib/api", async (orig) => {
  const actual = await orig<typeof import("@/lib/api")>();
  return {
    ...actual,
    listPromptExperiments: vi.fn(),
    listModels: vi.fn(),
    runExperiment: vi.fn(),
  };
});

import { ExperimentSection } from "@/components/ExperimentSection";

const listPromptExperiments = vi.mocked(api.listPromptExperiments);
const listModels = vi.mocked(api.listModels);
const runExperiment = vi.mocked(api.runExperiment);

const models: Model[] = [
  { model_id: "m1", name: "PromptDNA Echo", provider: "mock", created_at: "", execution_configured: true },
  { model_id: "m2", name: "GPT-5", provider: "OpenAI", created_at: "", execution_configured: false },
];

function exp(over: Partial<Experiment> = {}): Experiment {
  return {
    experiment_id: "e1",
    version_id: "v3",
    prompt_id: "p1",
    model_id: "m1",
    model_name: "PromptDNA Echo",
    provider: "mock",
    version_number: 3,
    executed_at: "2026-01-01T00:00:00Z",
    response_time_ms: 1420,
    score: null,
    output: null,
    notes: null,
    status: "SUCCESS",
    error_message: null,
    ...over,
  };
}

const props = {
  promptId: "p1",
  currentVersionId: "v3",
  currentVersionNumber: 3,
};

beforeEach(() => {
  listPromptExperiments.mockReset();
  listModels.mockReset();
  runExperiment.mockReset();
  listPromptExperiments.mockResolvedValue({ items: [], total: 0 });
  listModels.mockResolvedValue(models);
});

describe("ExperimentSection", () => {
  it("renders the experiments section", async () => {
    render(<ExperimentSection {...props} isOwner={false} />);
    expect(await screen.findByRole("region", { name: /experiments/i })).toBeInTheDocument();
    expect(await screen.findByText(/no experiments yet/i)).toBeInTheDocument();
  });

  it("owner sees Run Experiment; non-owner does not", async () => {
    const { rerender } = render(<ExperimentSection {...props} isOwner />);
    expect(await screen.findByRole("button", { name: /run experiment/i })).toBeInTheDocument();

    rerender(<ExperimentSection {...props} isOwner={false} />);
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: /run experiment/i })).not.toBeInTheDocument(),
    );
  });

  it("model selection works and shows the version under test", async () => {
    const user = userEvent.setup();
    render(<ExperimentSection {...props} isOwner />);
    await user.click(await screen.findByRole("button", { name: /run experiment/i }));
    const form = screen.getByRole("form", { name: /run experiment/i });
    expect(within(form).getAllByText(/version 3/i).length).toBeGreaterThanOrEqual(1);
    const select = within(form).getByLabelText(/model/i) as HTMLSelectElement;
    await waitFor(() => expect(select.value).toBe("m1")); // first configured model preselected
    await user.selectOptions(select, "m1");
    expect(select.value).toBe("m1");
  });

  it("shows a pending/running state while the experiment runs", async () => {
    const user = userEvent.setup();
    let resolve!: (e: Experiment) => void;
    runExperiment.mockReturnValue(new Promise<Experiment>((r) => (resolve = r)));
    render(<ExperimentSection {...props} isOwner />);
    await user.click(await screen.findByRole("button", { name: /run experiment/i }));
    const form = screen.getByRole("form", { name: /run experiment/i });
    await user.click(within(form).getByRole("button", { name: /^run experiment$/i }));
    expect(await within(form).findByText(/running experiment/i)).toBeInTheDocument();
    resolve(exp());
  });

  it("sends only model_id + notes and reloads the history on completion", async () => {
    const user = userEvent.setup();
    runExperiment.mockResolvedValue(exp());
    listPromptExperiments
      .mockResolvedValueOnce({ items: [], total: 0 })
      .mockResolvedValueOnce({ items: [exp()], total: 1 });
    render(<ExperimentSection {...props} isOwner />);
    await user.click(await screen.findByRole("button", { name: /run experiment/i }));
    const form = screen.getByRole("form", { name: /run experiment/i });
    await user.type(within(form).getByLabelText(/notes/i), "baseline");
    await user.click(within(form).getByRole("button", { name: /^run experiment$/i }));
    await waitFor(() => expect(runExperiment).toHaveBeenCalledTimes(1));
    expect(runExperiment).toHaveBeenCalledWith("p1", "v3", {
      model_id: "m1",
      notes: "baseline",
    });
    expect(await screen.findByText("PromptDNA Echo")).toBeInTheDocument();
  });

  it("displays a SUCCESS result with output and response time", async () => {
    listPromptExperiments.mockResolvedValue({
      items: [exp({ status: "SUCCESS", output: "MODEL SAID HELLO", response_time_ms: 1420 })],
      total: 1,
    });
    render(<ExperimentSection {...props} isOwner={false} />);
    expect(await screen.findByText("SUCCESS")).toBeInTheDocument();
    expect(screen.getByText("MODEL SAID HELLO")).toBeInTheDocument();
    expect(screen.getByText(/1\.42s/)).toBeInTheDocument();
    expect(screen.getByText(/not scored/i)).toBeInTheDocument();
  });

  it("displays a FAILED result with the error message and does not claim success", async () => {
    listPromptExperiments.mockResolvedValue({
      items: [exp({ status: "FAILED", output: null, error_message: "provider timed out" })],
      total: 1,
    });
    render(<ExperimentSection {...props} isOwner={false} />);
    expect(await screen.findByText("FAILED")).toBeInTheDocument();
    expect(screen.getByText(/provider timed out/i)).toBeInTheDocument();
    expect(screen.queryByText("SUCCESS")).not.toBeInTheDocument();
  });

  it("shows a score when present", async () => {
    listPromptExperiments.mockResolvedValue({
      items: [exp({ score: 8.5 })],
      total: 1,
    });
    render(<ExperimentSection {...props} isOwner={false} />);
    expect(await screen.findByText("8.5/10")).toBeInTheDocument();
  });
});
