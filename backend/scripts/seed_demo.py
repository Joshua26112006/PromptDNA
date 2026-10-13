"""Create (or top up) the PromptDNA demonstration account and dataset.

    cd backend
    # backend must be running (uvicorn app.main:app --port 8000)
    DEMO_PASSWORD='...' ./.venv/Scripts/python.exe scripts/seed_demo.py
    # or omit DEMO_PASSWORD and you will be prompted (nothing is stored).

DEMO DATA ONLY. Everything goes through the public HTTP API (register/login,
prompts, versions, experiments, scoring, embeddings), so it obeys the same
validation, ownership, versioning and lineage rules as real user data. There is
no direct SQL, no schema change and no Neo4j writes from this script — the
PostgreSQL -> Neo4j projection is run separately by ``scripts/sync_neo4j.py``
(this script invokes it at the end if ``--sync-graph`` is passed).

Idempotent and non-destructive: it only ever reads/creates records owned by the
demo user, matches prompts by title, and skips anything that already exists.
It never deletes anything.

Experiments run on the real ``mock`` provider only (the OpenAI key is not
assumed). Scores are *manually assigned demonstration scores*, not automatic
evaluations. Tags/collections have no write API, so none are created.
"""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

import httpx

DEMO_EMAIL = "demo.promptdna@example.com"
DEMO_NAME = "PromptDNA Demo User"
SCORE_NOTE = "Demo seed: manually assigned demonstration score (not an automatic evaluation)."
RUN_MARK = "[demo-seed]"

# --------------------------------------------------------------------------
# Dataset. Order matters: a parent must exist before its derived prompts.
# `experiments`: (version_number, score, note) — executed on the mock provider.
# --------------------------------------------------------------------------
PROMPTS: list[dict] = [
    {
        "title": "Academic Research Paper Summarizer",
        "description": "Condenses a scholarly research paper into a faithful, structured summary.",
        "purpose": "Academic summarization (category: Academic Research / Summarization)",
        "versions": [
            ("Summarize the research paper and identify the main objective, methodology, "
             "key findings, and conclusion.",
             "Initial version: a single free-form instruction."),
            ("Summarize the research paper in a structured format.\n\n"
             "Include:\n- Research objective\n- Methodology\n- Key findings\n"
             "- Limitations\n- Conclusion\n\nUse concise academic language.",
             "Added an explicit structure and a limitations section."),
            ("Analyze the following academic research paper and produce a concise, "
             "structured academic summary.\n\nInclude:\n\n1. Research objective\n"
             "2. Research problem\n3. Methodology\n4. Key findings\n5. Limitations\n"
             "6. Practical implications\n7. Conclusion\n\n"
             "Do not invent information that is not present in the source paper.",
             "Added research problem and practical implications; forbade invented content."),
        ],
        "experiments": [
            (1, 7, "Version 1 baseline run."),
            (2, 8, "Version 2 structured-format run."),
            (3, 9, "Version 3 run with the no-invention guardrail."),
            (3, 8, "Version 3 second run, different notes."),
        ],
    },
    {
        "title": "Research Article Analyzer",
        "description": "Critically analyzes a scholarly article's argument, evidence and methods.",
        "purpose": "Research paper analysis; derived from the Academic Research Paper Summarizer.",
        "parent": "Academic Research Paper Summarizer",
        "versions": [
            ("Read the scholarly research article below and analyze it. Summarize the "
             "research question, then evaluate the methodology, the strength of the "
             "evidence, and whether the conclusions follow from the results.",
             "Derived from the summarizer; shifts from summarizing to critical analysis."),
            ("Read the scholarly research article below and analyze it critically.\n\n"
             "1. Summarize the research question and hypotheses.\n"
             "2. Evaluate the methodology, sample, and data quality.\n"
             "3. Assess whether the conclusions follow from the evidence.\n"
             "4. List threats to validity and unanswered questions.\n\n"
             "Quote the article when making claims; do not rely on outside knowledge.",
             "Structured the critique and required evidence-based quotes."),
        ],
        "experiments": [(2, 8, "Analyzer v2 run.")],
    },
    {
        "title": "Literature Review Assistant",
        "description": "Synthesizes several scholarly papers into a literature review section.",
        "purpose": "Academic research writing; derived from the Research Article Analyzer.",
        "parent": "Research Article Analyzer",
        "versions": [
            ("Using the research article analyses below, write a literature review that "
             "groups the studies by theme and explains how they agree or disagree.",
             "Derived from the analyzer; extends one-paper analysis to many papers."),
            ("Using the research article analyses below, write a literature review "
             "section.\n\n- Group studies by theme, not by paper.\n"
             "- Compare methodologies and findings across studies.\n"
             "- Identify gaps in the research.\n- End with a short research-gap statement.\n\n"
             "Cite each study by author and year and summarize scholarly consensus carefully.",
             "Added thematic grouping and an explicit research-gap statement."),
        ],
        "experiments": [(2, 7, "Literature review v2 run.")],
    },
    {
        "title": "Python Code Reviewer",
        "description": "Reviews Python programs for correctness, style and maintainability.",
        "purpose": "Python code review (category: Programming).",
        "versions": [
            ("Review the following Python code and point out bugs and style problems.",
             "Initial version."),
            ("You are reviewing Python programs the way a careful senior engineer would. "
             "For the code below, list issues grouped as Correctness, Readability (PEP 8), "
             "Performance, and Security. Give a short fix for each issue.",
             "Grouped feedback by category and asked for concrete fixes."),
            ("You are reviewing Python programs the way a careful senior engineer would.\n\n"
             "For the code below:\n1. List issues grouped as Correctness, Readability (PEP 8), "
             "Performance, Security, and Testability.\n2. Show a corrected snippet for each "
             "important issue.\n3. Finish with an overall verdict: approve, approve with "
             "changes, or request changes.\n\nDo not rewrite the whole program.",
             "Added testability, corrected snippets and an overall verdict."),
        ],
        "experiments": [(3, 9, "Code reviewer v3 run.")],
    },
    {
        "title": "Python Debugging Assistant",
        "description": "Helps diagnose a Python error from a traceback and the surrounding code.",
        "purpose": "Python debugging (category: Programming).",
        "versions": [
            ("Here is a Python traceback and the code that produced it. Explain what "
             "caused the error and how to fix it.", "Initial version."),
            ("Here is a Python traceback and the code that produced it.\n\n"
             "1. Explain in plain language what the error means.\n"
             "2. Identify the exact line and the root cause.\n"
             "3. Propose a minimal fix and explain why it works.\n"
             "4. Suggest one test that would have caught the bug.",
             "Added root-cause analysis and a regression test suggestion."),
        ],
        "experiments": [(2, 8, "Debugging assistant v2 run.")],
    },
    {
        "title": "SQL Query Generator",
        "description": "Turns a plain-English question into a correct SQL query for a given schema.",
        "purpose": "SQL query generation (category: Databases).",
        "versions": [
            ("Given the database schema below, write a SQL query that answers the question.",
             "Initial version."),
            ("Given the PostgreSQL schema below, write a SQL query that answers the "
             "question. Use explicit JOINs, qualify every column with its table alias, "
             "and explain each clause briefly. If the question is ambiguous, state your "
             "assumption before the query.",
             "Specified PostgreSQL, explicit JOINs and assumption handling."),
        ],
        "experiments": [(2, 8, "SQL generator v2 run.")],
    },
    {
        "title": "Database Design Assistant",
        "description": "Guides a student through designing a normalized relational schema.",
        "purpose": "Database design and normalization (category: Databases).",
        "versions": [
            ("Help me design a relational database for the system described below. "
             "List the entities and their relationships.", "Initial version."),
            ("Help me design a normalized relational database for the system described "
             "below.\n\n1. Identify entities, attributes, and relationships.\n"
             "2. Propose tables with primary and foreign keys and cardinalities.\n"
             "3. Show the functional dependencies and justify 3NF.\n"
             "4. Suggest indexes for the most likely queries.",
             "Added keys, functional dependencies, 3NF justification and indexes."),
        ],
        "experiments": [(2, 8, "Database design assistant v2 run.")],
    },
    {
        "title": "Exam Preparation Study Planner",
        "description": "Builds a day-by-day revision plan and practice questions for an exam.",
        "purpose": "Exam preparation (category: Study skills).",
        "versions": [
            ("I have an exam in two weeks on the topics listed below. Create a day-by-day "
             "revision plan that balances new material, review and practice questions.",
             "Initial version."),
        ],
        "experiments": [],
    },
    {
        "title": "Technical Concept Explainer",
        "description": "Explains a technical concept at the reader's level with an analogy and example.",
        "purpose": "Technical explanation (category: Learning).",
        "versions": [
            ("Explain the technical concept below to a student who is new to it.",
             "Initial version."),
            ("Explain the technical concept below to a student who is new to it.\n\n"
             "Start with a one-sentence definition, then an everyday analogy, then a small "
             "concrete example, and end with two common misconceptions.",
             "Added analogy, example and misconceptions."),
        ],
        "experiments": [],
    },
    {
        "title": "Data Analysis Report Assistant",
        "description": "Turns a dataset summary into a short, honest analysis report.",
        "purpose": "Data analysis (category: Analytics).",
        "versions": [
            ("Given the dataset summary and statistics below, write a short report "
             "describing the main trends, outliers and a recommended next step. "
             "Do not claim causation from correlation alone.", "Initial version."),
        ],
        "experiments": [],
    },
]


class Api:
    def __init__(self, base: str) -> None:
        self.http = httpx.Client(base_url=base.rstrip("/") + "/api/v1", timeout=60.0)
        self.token: str | None = None

    def _h(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def call(self, method: str, path: str, *, ok: tuple[int, ...] = (200, 201), **kw):
        r = self.http.request(method, path, headers=self._h(), **kw)
        if r.status_code not in ok:
            raise SystemExit(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r


def ensure_account(api: Api, password: str) -> None:
    r = api.http.post("/auth/register", json={"email": DEMO_EMAIL, "password": password,
                                              "name": DEMO_NAME})
    if r.status_code == 201:
        print(f"account: created {DEMO_EMAIL}")
    elif r.status_code == 409:
        print(f"account: {DEMO_EMAIL} already exists (reused)")
    else:
        raise SystemExit(f"register failed: {r.status_code} {r.text[:200]}")
    r = api.http.post("/auth/login", data={"username": DEMO_EMAIL, "password": password})
    if r.status_code != 200:
        raise SystemExit("login failed — wrong DEMO_PASSWORD for the existing demo account?")
    api.token = r.json()["access_token"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base-url", default=os.environ.get("API_BASE_URL", "http://localhost:8000"))
    ap.add_argument("--sync-graph", action="store_true",
                    help="run scripts/sync_neo4j.py afterwards (PostgreSQL -> Neo4j)")
    args = ap.parse_args()

    password = os.environ.get("DEMO_PASSWORD") or getpass.getpass("Demo account password: ")
    api = Api(args.base_url)
    ensure_account(api, password)
    me = api.call("GET", "/auth/me").json()

    models = api.call("GET", "/models").json()
    mock_models = [m for m in (models["items"] if isinstance(models, dict) else models)
                   if m["provider"] == "mock" and m["execution_configured"]]
    if not mock_models:
        raise SystemExit("no executable mock model found; cannot create experiments")
    model = mock_models[0]
    print(f"experiments run on: {model['name']} (provider={model['provider']})")

    mine: dict[str, dict] = {}
    page = api.call("GET", "/prompts", params={"limit": 100}).json()
    for it in page["items"]:
        if it["user_id"] == me["user_id"]:
            mine[it["title"]] = it

    counts = {"prompts": 0, "versions": 0, "experiments": 0, "scores": 0, "embeddings": 0}
    for spec in PROMPTS:
        title = spec["title"]
        if title in mine:
            pid = mine[title]["prompt_id"]
        else:
            body = {"title": title, "content": spec["versions"][0][0],
                    "description": spec["description"], "purpose": spec["purpose"],
                    "is_public": False}
            if spec.get("parent"):
                body["parent_prompt_id"] = mine[spec["parent"]]["prompt_id"]
            created = api.call("POST", "/prompts", json=body).json()
            pid = created["prompt_id"]
            mine[title] = created
            counts["prompts"] += 1
            counts["versions"] += 1
            print(f"prompt: created '{title}'")

        detail = api.call("GET", f"/prompts/{pid}").json()
        have = {v["version_number"]: v for v in detail["versions"]}
        for n, (content, summary) in enumerate(spec["versions"], start=1):
            if n in have:
                if have[n]["content"] != content:
                    print(f"  warn: '{title}' v{n} exists with different content; left untouched")
                continue
            if n != max(have, default=0) + 1:
                print(f"  warn: '{title}' skipping out-of-order v{n}")
                continue
            v = api.call("POST", f"/prompts/{pid}/versions",
                         json={"content": content, "change_summary": summary}).json()
            have[v["version_number"]] = v
            counts["versions"] += 1
            print(f"  version: '{title}' v{n} created")

        # embeddings (existing pipeline; owner-only)
        for n, v in sorted(have.items()):
            st = api.call("GET", f"/versions/{v['version_id']}/embedding").json()
            if not st["has_embedding"]:
                api.call("POST", f"/versions/{v['version_id']}/embedding")
                counts["embeddings"] += 1

        # experiments (real mock-provider runs) + manual demonstration scores
        existing = api.call("GET", f"/prompts/{pid}/experiments").json()["items"]
        used = {e["notes"] for e in existing if e["notes"]}
        for vnum, score, note in spec["experiments"]:
            marker = f"{RUN_MARK} {note}"
            if any(u.startswith(marker) for u in used) or vnum not in have:
                continue
            exp = api.call("POST", f"/prompts/{pid}/versions/{have[vnum]['version_id']}/experiments",
                           json={"model_id": model["model_id"], "notes": marker}).json()
            counts["experiments"] += 1
            if exp["status"] != "SUCCESS":
                print(f"  warn: experiment for '{title}' v{vnum} ended {exp['status']} — not scored")
                continue
            api.call("PATCH", f"/experiments/{exp['experiment_id']}",
                     json={"score": score, "notes": f"{marker} {SCORE_NOTE}"})
            counts["scores"] += 1
            print(f"  experiment: '{title}' v{vnum} run on mock, score {score}/10 (manual)")

    print("\nNEW THIS RUN:", counts)
    if args.sync_graph:
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
        subprocess.run([sys.executable, str(Path(__file__).with_name("sync_neo4j.py"))],
                       check=True, env=env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
