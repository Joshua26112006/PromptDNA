# PromptDNA — Frontend

Next.js (App Router) + React + TypeScript + Tailwind CSS.

**Phase 4B scope: the authenticated Prompt Library + Prompt Detail experience.**
No dashboard, tags, collections, graph, analytics, or semantic-search UI yet.

## Requirements

- Node.js 20+ (developed on Node 24)
- A running backend (see `../backend/README.md`).

## Setup

```bash
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL (default http://localhost:8000)
```

## Run

```bash
npm run dev      # http://localhost:3000
npm run build    # production build
npm run start    # serve the production build
npm run lint     # eslint
npm run test     # vitest (jsdom + React Testing Library) — no backend needed
```

## Structure

```
lib/
  types.ts          TypeScript shapes mirroring the FastAPI schemas
  api.ts            centralized client: base URL, bearer header, JSON, friendlyMessage(err)
  auth-context.tsx  <AuthProvider> + useAuth() → { user, status, loading, login, register, logout }

components/
  ProtectedShell.tsx  auth gate (spinner while loading; redirect to /login if unauth)
  AppShell.tsx        header: PromptDNA brand, Prompt Library nav, current user, Log out
  PromptCard.tsx      one library row (title, description, visibility, latest version, updated)
  VisibilityBadge.tsx PUBLIC / PRIVATE — text label + icon, never colour-only
  Pagination.tsx      Previous / Page X of Y / Next (offset/limit/total)
  VersionHistory.tsx  selectable list, newest first, CURRENT marker, no edit/delete controls
  VersionPanel.tsx    read-only display of one version (content, summary, created, creator)
  CreateVersionForm.tsx  owner-only; POSTs { content, change_summary } only
  EditMetadataForm.tsx   owner-only; PATCHes title/description/purpose/is_public only
  ui.tsx              Spinner, ErrorBox, InfoNote, TextField, TextAreaField, buttons

app/
  page.tsx                    routes to /prompts or /login by auth state
  login/page.tsx              email + password → token → /prompts
  register/page.tsx           name + email + password → auto-login → /prompts
  (app)/layout.tsx            wraps the group in <ProtectedShell>
  (app)/prompts/page.tsx      Prompt Library: search, visibility filter, grid, pagination
  (app)/prompts/new/page.tsx  create prompt (+ Version 1)
  (app)/prompts/[prompt_id]/page.tsx  detail: metadata, current version, history, lineage,
                                      owner-only Edit Metadata / Create New Version
```

## Notes

- **Backend is authoritative.** Hidden buttons are UX only — the API enforces
  authentication, ownership, visibility, validation, version numbering and
  immutability. Non-owners simply never see write controls.
- **Search is lexical** (PostgreSQL `ILIKE` on title). Semantic search is not
  implemented yet — it is a later phase (pgvector).
- **Token storage:** `localStorage` (Phase 3). XSS trade-off documented in
  `../docs/decisions.md`. Logout is client-side only (drops the token).
- `AGENTS.md` / `CLAUDE.md` are `create-next-app` guidance files.
