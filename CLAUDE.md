# CLAUDE.md

This file gives Claude (and Cursor, and any other coding agent) context about this repo so it generates consistent code across sessions and across teammates. Read this first when starting work.

> **First-time setup:** these are starting conventions. Both teammates should read through, edit anything you disagree with, and commit the final version together before either of you starts writing features. Once it's committed, treat it as the agreement.

## What this project is

A web app for UATX students to buy and sell used textbooks from each other. The defining feature is course-history-based matching: when a freshman needs the book for PHIL 101, the app surfaces listings from upperclassmen who took PHIL 101 in past semesters. Buyers and sellers chat in-app, scoped to a specific listing.

This is a 3-week final project for UATX's Software Engineering course (Spring 2026). Targeting silver tier, with gold reachable if everything goes well.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (ORM), Postgres
- **Frontend:** TypeScript, React, Vite, React Router for routing
- **Database:** Postgres hosted on Supabase
- **Auth:** Supabase Auth (JWT-based; FastAPI verifies tokens server-side)
- **Hosting:** Railway. FastAPI serves the built React bundle at `/` and handles API requests at `/api/*` — one service, one URL, no CORS.
- **Tests:** pytest (backend), Vitest (frontend)
- **CI:** GitHub Actions, runs on every push and PR, blocks merge to `main` on failure

## Repo layout

```
/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── routers/             # one file per resource (listings.py, messages.py, ...)
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── db.py                # session, engine
│   │   └── auth.py              # JWT verification dependency
│   ├── tests/                   # pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # top-level routed components
│   │   ├── components/          # reusable UI
│   │   ├── hooks/               # custom React hooks
│   │   ├── lib/                 # api client, supabase client, utilities
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── .github/workflows/
│   └── test.yml                 # CI workflow
├── SCHEMA.md                    # source of truth for the data model
├── CLAUDE.md
└── README.md
```

## Team ownership

Two people. Ownership is by feature seam, end-to-end (table → API → frontend → tests).

- **Person A — marketplace half:** listings (create/browse/search/detail), the course-matching algorithm and feed. Files in `routers/listings.py`, `routers/matching.py`, plus the listings/browse/detail pages on the frontend.
- **Person B — people half:** auth integration, user profiles, course-history capture, messaging between buyer and seller. `routers/auth.py`, `routers/profiles.py`, `routers/messages.py`, plus the corresponding frontend pages and the chat UI.

Shared boundaries (touch carefully, talk first):
- `users` / `profiles` table (Person B owns, A reads via FK)
- `listings` table (Person A owns, B's messages table FKs into it)
- `enrollments` / course-history shape (Person B captures, A's matching reads)

When in doubt about whether you can touch something: if it's on the other person's list above, ask before changing it.

## Backend conventions

- All API routes live under `/api/`. The React app is served at `/`.
- One router file per resource. Routes follow REST-ish patterns: `GET /api/listings`, `GET /api/listings/{id}`, `POST /api/listings`, etc.
- Every request that touches user-scoped data goes through the JWT auth dependency. Get the user from the verified JWT — never from a header, query param, or request body.
- Pydantic models for every request and response. Don't return SQLAlchemy models directly to the client.
- Error responses are FastAPI `HTTPException` with a status code and a `detail` string. Validation errors come back as 422 from Pydantic automatically.
- Database access goes through a `get_db()` dependency that yields a session and closes it after the request.
- Don't write raw SQL unless there's a real reason (e.g. an aggregation that's awkward in the ORM). When you do, parameterize — never f-string user input into a query.

## Frontend conventions

- TypeScript strict mode. No `any` without a comment explaining why.
- Every fetch has a visible loading state AND a visible error state. This is graded and also just correct.
- Data fetching: plain `fetch` wrapped in a small `api` client in `lib/api.ts`. Promote to React Query if/when we hit refetch/cache complexity — not before.
- Routing via React Router. URLs are bookmarkable. Refreshing keeps you where you are. Back button works.
- Functional components with hooks. No class components.
- Tailwind for styling. Prefer utility classes; bail to a component CSS file if a piece gets gnarly.
- Forms: controlled components. Disable the submit button while the request is in flight.

## Database conventions

- snake_case for tables and columns.
- Real foreign keys with `ON DELETE` behavior chosen explicitly (usually `CASCADE` for child rows, `RESTRICT` for parents that shouldn't disappear).
- `NOT NULL` is the default; only nullable when there's a real reason, and document why in the column comment.
- Every table has `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`. Tables that mutate get `updated_at TIMESTAMPTZ` too.
- UUIDs for primary keys (matches Supabase Auth user IDs; keeps the whole schema consistent).
- Length limits on text columns where appropriate (titles, names, body text).
- See `SCHEMA.md` for the actual table definitions — don't duplicate them here.

## Tests

- Backend: pytest, in `backend/tests/`, files named `test_*.py`. Each test is independent — sets up its data, asserts, cleans up.
- Frontend: Vitest, tests next to the file they test as `*.test.ts(x)`.
- Cover the happy path AND at least one edge case for every nontrivial endpoint. Edge cases that actually matter here: not-logged-in, logged-in-as-wrong-user, missing required fields, conflicting state (e.g. buying your own listing, messaging on a sold listing).
- Don't pile up five tests for trivial CRUD. Spend the test budget on the logic that has real failure modes — the matching algorithm, the messaging state, auth gating.

## Git workflow

- `main` is protected. Direct pushes blocked. Merge via PR only.
- Feature branches: `feat/<short-description>` or `fix/<short-description>`.
- PRs are small, scoped, and described in a sentence or two: what changes, why, what to look at first.
- CI must pass before you ask the other person to review. Look at the red X yourself first.
- Real commit history from both people. Squash if you want, but don't let one person commit a week's worth of the other person's work.

## Things NOT to do

- Don't use SQLite in dev. Connect to the cloud Postgres so dev and prod match.
- Don't use the `X-Username` header pattern from A2 / A4. User identity comes from the verified JWT, full stop.
- Don't denormalize fields that should be foreign keys. No `seller_name` on `listings` — join to `users`.
- Don't put secrets in the repo. Supabase keys, DB URLs, JWT secrets all go in environment variables — Railway dashboard for prod, GitHub Actions secrets for CI, local `.env` files (gitignored) for dev.
- Don't `print()` for debugging in committed code. Use logging or remove it before the PR.
- Don't skip loading/error states on a fetch. "I'll add it later" means "I'll forget."
- Don't write a test after the feature ships and call it covered. A real test could have failed and caught a real bug.
- Don't change a shared table (`users`, `listings`, `enrollments`) without talking to the other person first.

## Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env  # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_URL
npm run dev

# Tests
cd backend && pytest
cd frontend && npm run test
```

## The nontrivial piece (Person A owns)

The course-matching algorithm lives in `backend/app/routers/matching.py`. When called for a logged-in user, it:

1. Reads the user's current enrolled courses
2. Looks up the required books for those courses from `course_books`
3. Finds open listings for those books
4. Filters out listings posted by the viewing user themselves
5. Ranks the results (see open questions below)
6. Returns the ranked list

**Open design decisions, to be settled by end of week 1:**
- Book identity: edition-aware match, or fuzzy on title + author?
- Ranking signal: recency of the seller having taken the course, listing freshness, price, something else? What's the tiebreaker?
- Source of "courses I'm enrolled in": Populi API (if we can get access), or self-report at signup?

Document the final answers in this section once decided. At the demo, Person A should be able to walk through how this works without notes.
