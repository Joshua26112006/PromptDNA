# PromptDNA — Frontend

Next.js (App Router) + React + TypeScript + Tailwind CSS.

**Phase 3 scope: authentication UI only** — `/login`, `/register`, and a home
page that shows the signed-in user (`/api/v1/auth/me`) with a logout button. No
dashboard / prompt library / analytics / graph UI yet.

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
```

## Auth flow

- `lib/api.ts` — `register()`, `login()` (OAuth2 form; `username` = email),
  `me()`, and token helpers.
- `lib/auth-context.tsx` — `<AuthProvider>` + `useAuth()` (`user`, `loading`,
  `login`, `register`, `logout`).
- `app/login/page.tsx`, `app/register/page.tsx`, `app/page.tsx`.

### Token storage — security trade-off

The access token is kept in **`localStorage`** for this development build and
sent as `Authorization: Bearer <token>`. `localStorage` is readable by any
script on the origin, so a successful XSS would leak the token. This is **not**
claimed to be production-secure — a production build should use an HttpOnly,
Secure, SameSite cookie issued by the backend (with CSRF protection). See
`../docs/decisions.md` (Decision 31).

Logout is client-side only (stateless JWT): it deletes the stored token.

## Notes / testing

- `AGENTS.md` / `CLAUDE.md` are `create-next-app` guidance files — kept for
  reference.
- There is no browser test framework in this project yet, so frontend
  verification is: `npm run build` (all routes compile) + `npm run lint` +
  manual end-to-end against a running backend. Adding Playwright/Vitest is
  deferred (out of scope for this phase).
