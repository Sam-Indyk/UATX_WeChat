# CLAUDE.md

Context for any coding agent (Claude, Cursor, etc.) and any teammate picking up the project. Read this first when starting work.

> **How we work on this project.** We work sequentially, one person at a time, mostly driving via Claude. Whoever's next reads the **Runway** section at the bottom, picks up the next undone step, finishes it, ticks it off, and commits. Treat the runway as the source of truth for "what's next."

## What this project is

A web app for UATX students to buy and sell used textbooks from each other. The defining feature is **course-history-based matching**: when a freshman needs the book for PHIL 101, the app surfaces listings from upperclassmen who took PHIL 101 in past semesters. Buyers and sellers chat in-app, scoped to a specific listing.

This is the 3-week final project for UATX's Software Engineering course (Spring 2026). **Target tier: Gold.** Bronze is the floor.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (ORM), Alembic (migrations), Postgres.
- **Frontend:** TypeScript, React, Vite, React Router, Tailwind.
- **Database:** Postgres. Locally via Docker Compose. In production via Supabase Postgres (we use Supabase for the DB only — not for auth).
- **Auth:** Clerk with Google sign-in, restricted to `@student.uaustin.org`. Clerk issues a JWT; FastAPI verifies it server-side against Clerk's JWKS.
- **Hosting:** Railway. FastAPI serves the built React bundle at `/` and handles API requests at `/api/*` — one service, one URL, no CORS in prod.
- **Tests:** pytest (backend), Vitest (frontend).
- **CI:** GitHub Actions. Runs on every push and PR. Blocks merge to `main` on failure. Deploy gated on green.

## Repo layout

```
/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── config.py            # settings loaded from env
│   │   ├── db.py                # SQLAlchemy engine + session
│   │   ├── auth.py              # Clerk JWT verification dependency
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── routers/             # one file per resource
│   ├── alembic/                 # migrations
│   ├── tests/                   # pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/               # top-level routed components
│   │   ├── components/          # reusable UI
│   │   ├── hooks/               # custom React hooks
│   │   └── lib/                 # api client, clerk helpers, utilities
│   ├── package.json
│   └── vite.config.ts
├── .github/workflows/
│   └── test.yml                 # CI
├── docker-compose.yml           # local Postgres
├── SCHEMA.md                    # the data model, in words
├── CLAUDE.md
└── README.md
```

## Backend conventions

- All API routes live under `/api/`. The React app is served at `/`.
- One router file per resource. Routes follow REST-ish patterns.
- Every user-scoped route goes through the Clerk JWT auth dependency (`auth.require_user`). Get the user from the verified JWT — never from a header, query param, or request body.
- Pydantic models for every request and response. Don't return SQLAlchemy models directly to the client.
- Error responses are FastAPI `HTTPException` with a status and `detail`. Validation errors come back as 422 from Pydantic automatically.
- Database access goes through a `get_db()` dependency that yields a session and closes it after the request.
- Don't write raw SQL unless there's a real reason. When you do, parameterize.

## Frontend conventions

- TypeScript strict mode. No `any` without a comment.
- Every fetch has a visible loading state AND a visible error state.
- Data fetching: plain `fetch` wrapped in `lib/api.ts`, which attaches the Clerk token automatically. Promote to React Query only if we hit real refetch/cache complexity.
- Routing via React Router. URLs are bookmarkable. Refreshing keeps you where you are. Back button works.
- Functional components with hooks. No class components.
- Tailwind for styling.
- Forms: controlled components. Disable submit while in flight.

## Database conventions

- snake_case for tables and columns.
- Real foreign keys with `ON DELETE` chosen explicitly.
- `NOT NULL` is the default; nullable only when there's a real reason.
- Every table has `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`. Mutable tables also have `updated_at TIMESTAMPTZ`.
- UUIDs for primary keys, except `users.id` which is the Clerk user ID (a string like `user_2abc...`). This makes JWT verification → DB lookup trivial.
- See `SCHEMA.md` for table definitions.

## Tests

- Backend: pytest in `backend/tests/`. Each test independent — sets up, asserts, cleans up.
- Auth in tests: override the `require_user` dependency to inject a fake user. Don't mock Clerk's JWKS.
- Frontend: Vitest, tests next to the file they test as `*.test.ts(x)`.
- Cover happy path AND at least one edge case for every nontrivial endpoint.

## Things NOT to do

- Don't use SQLite, even for local dev. Use Docker Postgres so dev and prod match.
- Don't use the `X-Username` header pattern. User identity = verified Clerk JWT.
- Don't denormalize fields that should be foreign keys.
- Don't put secrets in the repo.
- Don't `print()` for debugging in committed code.
- Don't skip loading/error states on a fetch.

## Local development

Prereqs: Python 3.12, Node 20+, Docker Desktop.

```bash
# 1. Bring up Postgres
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate           # Windows
pip install -r requirements.txt
copy .env.example .env           # fill in CLERK_* values
alembic upgrade head             # apply migrations
uvicorn app.main:app --reload    # http://localhost:8000

# 3. Frontend (separate terminal)
cd frontend
npm install
copy .env.example .env           # fill in VITE_CLERK_PUBLISHABLE_KEY, VITE_API_URL=http://localhost:8000
npm run dev                      # http://localhost:5173

# Tests
cd backend
pytest
cd frontend
npm run test
```

## Auth: how Clerk fits

- Clerk owns sign-in UI and the Google OAuth dance. We use `<SignIn />` from `@clerk/clerk-react`.
- Sign-in restricted to `@student.uaustin.org` via Clerk's restriction settings.
- Every request to `/api/*` sends `Authorization: Bearer <clerk-jwt>`.
- Backend verifies the JWT against Clerk's JWKS. On success it extracts the Clerk user ID (`sub`) and uses that as `users.id`.
- First request from a new Clerk user upserts the `users` row (display name, email, avatar URL from JWT claims).

## The nontrivial pieces

### Piece 1 (bronze): course-matching algorithm

`backend/app/routers/matching.py` → `match_listings_for_user`. For a signed-in user:

1. Read the user's current enrollments (`is_current = true`).
2. Find active listings whose `course_id` is in that set.
3. Exclude the user's own listings.
4. Rank by:
   - **Primary:** seller's "course recency" — how recently the seller was enrolled in the same course. More recent = higher rank (book more likely the current edition).
   - **Tiebreaker 1:** listing freshness (newer first).
   - **Tiebreaker 2:** lower price first.
5. Return the ranked list with seller display name and a rationale string ("Seller took PHIL 101 in Fall 2024").

Edge cases that matter: user has no current enrollments, no listings match, all matches are the user's own.

### Piece 2 (silver): TBD

Candidates:
- **Price suggestion** when posting a listing, based on past sold listings of the same book + condition.
- **Conversation state machine** — listings move through `active → reserved → sold`; conversations move through `inquiry → offer → counter → accepted/declined`.
- **Graduating-seller feed** — listings whose seller has no current enrollments but a heavy course history. Decay function.

Pick one when we get to silver.

### Gold custom features (need 2)

Brainstorming bucket:
- Saved searches with notifications.
- Seller reputation after completed sales.
- Bundle deals.
- A "wanted" board.

Pick two when we get there.

### Gold "pick one"

Most likely **real-time-ish chat via polling**. Lowest risk, fits the product. Alternative: full Playwright e2e suite.

## Runway

Read this section, find the next undone step, do it, tick it off, commit. Acceptance criteria below each step.

Status: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked

---

### Phase 0: Foundation

- [x] **CLAUDE.md and README rewritten as runway.** Reflect Clerk + Supabase Postgres + Docker local. SCHEMA.md committed.
- [x] **Docker Compose for local Postgres.** `docker compose up -d` brings up Postgres 16 on `localhost:5432`.
- [x] **Backend scaffold runs.** `uvicorn app.main:app --reload` boots, `GET /api/health` returns 200.
- [x] **SQLAlchemy models + initial Alembic migration.** All tables in SCHEMA.md exist after `alembic upgrade head`.
- [x] **Clerk JWT auth dependency.** `require_user` fetches and caches JWKS, verifies tokens, upserts and returns the DB user.
- [x] **First routers + Pydantic schemas.** `me`, `courses`, `listings`, `messages`, `matching`.
- [x] **Pytest scaffold with dependency-override auth.** ~9 tests covering main paths + edge cases.
- [x] **Frontend scaffold runs.** `npm run dev` boots Vite on `:5173`. Tailwind compiles. React Router renders pages.
- [x] **Clerk integration on the frontend.** `<ClerkProvider>` at the root, sign-in page, protected routes, `getToken()` plumbed into the api client.
- [x] **Sign-in → onboarding → listings stubbed.** Pages render with loading and error states.
- [x] **One Vitest test.**
- [x] **GitHub Actions CI.** Runs backend pytest + frontend vitest on every push.

### Phase 1: Bronze (next)

- [ ] **Get Clerk keys.** Create a Clerk app, enable Google as the only social provider, configure the `@student.uaustin.org` email restriction, copy `VITE_CLERK_PUBLISHABLE_KEY` and `CLERK_JWKS_URL` into `.env` files. ~10 min.
- [ ] **Create Supabase Postgres project.** Get the pooled connection string, save it somewhere private. We'll use it on Railway.
- [ ] **Seed UATX courses.** Script (or data migration) populating the `courses` table with the actual UATX catalog.
- [ ] **Onboarding flow polished.** After first sign-in, redirect new users to `/onboarding` where they pick current courses. Persisted to `enrollments` with `is_current = true`.
- [ ] **Listings: browse + filter by course.** List page hits `GET /api/listings?course_id=...`, clean grid, loading + error states.
- [ ] **Listings: detail page.** Full info, seller name, "Message seller" button.
- [ ] **Listings: create.** Form posts to `POST /api/listings`. (Photo upload via Supabase Storage is silver/gold.)
- [ ] **Messaging: inbox + thread.** Inbox lists conversations; thread shows messages with a send box. No polling yet.
- [ ] **Matching: live at `/match`.** Calls `GET /api/match`, renders ranked feed.
- [ ] **Tests: top up to ~10.** At least one edge-case test per nontrivial endpoint.
- [ ] **Deploy to Railway.** FastAPI serves the React bundle at `/`. One URL. DATABASE_URL → Supabase. Clerk production keys.
- [ ] **README "Live URL" filled in. Bronze achieved.**

### Phase 2: Silver

- [ ] Pick + build the second nontrivial piece.
- [ ] Optimistic updates on at least one action (posting a listing or sending a message), with rollback.
- [ ] Confirm bookmarkable URLs and back button work end to end.
- [ ] Visual design pass with Tailwind: type scale, color palette, spacing, deliberate components.
- [ ] Extra tests for silver behavior or one e2e-ish test (Playwright).

### Phase 3: Gold

- [ ] Mobile pass. Every page works on phone width. No horizontal scrolling. Tap targets ≥ 44px.
- [ ] Pick-one: real-time chat via polling (recommended), or Playwright e2e, or design with a point of view.
- [ ] Custom feature 1: TBD.
- [ ] Custom feature 2: TBD.
- [ ] README updated with gold-tier description.

---

## Note on team spec

The Final Project spec requires 2-3 people. We work sequentially via Claude, but **commits must come from real teammates** for the project to count. Coordinate so every teammate has meaningful commits in `git log` by demo day.
