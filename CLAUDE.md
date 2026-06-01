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
- **Auth:** Clerk with Google sign-in. Open to any Google account (we don't restrict to `@student.uaustin.org` because incoming students who haven't been issued their school email yet should still be able to buy books). Clerk issues a JWT; FastAPI verifies it server-side against Clerk's JWKS. If we later want a domain restriction we can re-enable it by setting `ALLOWED_EMAIL_DOMAINS` on the backend.
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
- Sign-in is open to any Google account — we explicitly do NOT restrict to `@student.uaustin.org`, because incoming students who don't have their school email yet still need to buy books from upperclassmen.
- The backend has an `ALLOWED_EMAIL_DOMAINS` env var that, if set, enforces a server-side allowlist. Leaving it empty (the default) means any email is fine.
- Every request to `/api/*` sends `Authorization: Bearer <clerk-jwt>`.
- Backend verifies the JWT against Clerk's JWKS. On success it extracts the Clerk user ID (`sub`) and uses that as `users.id`.
- First request from a new Clerk user upserts the `users` row (display name, email, avatar URL from JWT claims).

## The nontrivial pieces

### Piece 1 (bronze): course-matching algorithm

`backend/app/routers/matching.py` → `match_listings_for_user`. For a signed-in user:

1. Read the user's enrollments that are either **current** or **upcoming** — those are the courses they might need books for.
2. Find active listings whose `course_id` is in that set.
3. Exclude the user's own listings.
4. Rank by:
   - **Primary:** seller's "course recency" — how recently the seller was enrolled in the same course. More recent = higher rank (book more likely the current edition). A seller who took it last semester (status=past, recent term) outranks one who took it three years ago.
   - **Tiebreaker 1:** listing freshness (newer first).
   - **Tiebreaker 2:** lower price first.
5. Return the ranked list with seller display name and a rationale string ("Seller took PHIL 101 in Fall 2024").

Edge cases that matter: user has no current/upcoming enrollments, no listings match, all matches are the user's own.

**Note on enrollment status:** the algorithm distinguishes three states per enrollment — `past`, `current`, `upcoming`. Buyers need books for `current` and `upcoming` courses; sellers typically have books from `past` and `current` courses they took. See the Phase 1 runway item for the schema change.

### Piece 2 (silver): classmates lookup

`backend/app/routers/classmates.py` → `GET /api/classmates`. For a signed-in user, returns other students who share at least one of their current courses, grouped per classmate with the list of shared courses. Real cross-table aggregation across `users` × `enrollments` (self-join to find course overlap), with filters: only `is_current=true` enrollments count, the requesting user is excluded, classmates are deduplicated even when they share multiple courses.

Edge cases covered in `tests/test_classmates.py`: no enrollments returns empty, past enrollments don't count, multi-course-shared classmates appear once with the full shared-courses list, the user never appears in their own classmate list.

### Gold custom features (need 2)

Our two:

1. **General-purpose marketplace ("Everything Else" tab).** Listings stop being book-only. A new `category` field lets users sell furniture, electronics, sports gear, clothing, etc. — anything that makes sense between UATX students. The home page grows a tab that shows non-book listings with category filters and search. The course-matching feed continues to only surface book listings tied to courses; the general marketplace is its own surface. Schema work + UI work + real category-based browsing.

2. **Image uploads on listings.** Optional, single image per listing for now. Stored in Supabase Storage (we're already on Supabase). Authenticated upload (only the listing's seller). Public read URL written to a new `image_url` column on `listings`. Real concerns to handle: file size limits, MIME-type validation, what to do when no image is provided.

Bonus features we already have or are likely to add:
- **Classmates view** (already shipped — see Piece 2 above).
- **Seller profile page** clickable from a listing — shows their other active listings and a "Message me" button.

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

### Phase 1: Bronze (in progress)

- [x] **Get Clerk keys.** Clerk app `related-sunbird-55` created, Google enabled, sign-in open to all Google accounts (no email-domain restriction). Keys in `frontend/.env` and `backend/.env`.
- [x] **Create Supabase Postgres project.** `uatx-wechat` project on aws-1-us-west-1, pooler URL in Railway env vars, migrations applied (6 tables + alembic_version).
- [x] **Deploy to Railway.** Dockerfile + railway.toml, FastAPI serves the React bundle at `/`. Live at https://uatxwechat-production.up.railway.app. CORS off in prod (same-origin). Migrations run on container start.
- [x] **README "Live URL" filled in.**
- [x] **Seed UATX courses.** Data migration `0002_seed_courses.py` inserts the full 2025-26 UATX catalog (167 courses across INF/ALT/EPH/STM/POL/EDU). Idempotent (`ON CONFLICT DO NOTHING`).
- [x] **Onboarding flow polished.** Search + center-filter UI over the 167 courses, selections persist to `enrollments` with `is_current=true`.
- [ ] **Enrollment kind: past / current / upcoming.** Replace `enrollments.is_current` (boolean) with `kind` enum (`past`, `current`, `upcoming`). Migrate existing data: rows with `is_current=true` become `current`, rows with `is_current=false` become `past` (we have no `upcoming` data yet). Update Onboarding UI to let users mark each course as one of the three states (default current). Update matching to surface books for the user's `current` AND `upcoming` courses (not just current). Update classmates to optionally include upcoming-shared classes. Add tests for the new states.
- [x] **Smoke-test bronze end-to-end on the live URL.** First pass found three things: (a) SPA routing broken — backend wasn't falling back to index.html for React Router paths, breaking sign-in (fixed in PR #7). (b) Authenticated endpoints 500'd on the second-ever sign-in because the default Clerk JWT has no email claim and the empty-string fallback collided on the `users.email` UNIQUE constraint (fixed in PR #8 with a synthesized `<sub>@clerk.local` fallback). (c) "Linear algebra book missing from /match" was working as designed — `/match` excludes your own listings, requires a second account to test. Listings + chat verified working end-to-end with two accounts.
- [x] **Listings: browse + filter by course.** Verified working live.
- [x] **Listings: detail page.** Verified working live.
- [x] **Listings: create.** Verified working live with a real course-tagged book.
- [x] **Messaging: inbox + thread.** Verified working live between two accounts.
- [x] **Matching: live at `/match`.** Renders, links to listings, shows rationale.
- [x] **Search-first course pickers everywhere.** New `<CourseSearchPicker>` component in `frontend/src/components/`. Single-select combobox: input + filtered dropdown, opens on focus, closes on selection/Esc/click-outside, top-100 cap with a "narrow further" hint. Used on the New Listing form's course field and the Listings page's filter. Onboarding keeps its dedicated search-and-filter UX (multi-select + per-row kind dropdown wouldn't fit the combobox pattern).
- [x] **Enrollment kind: past / current / upcoming.** Migration `0005` drops `enrollments.is_current` and adds `kind` enum (CHECK in `('past','current','upcoming')`). Existing data backfilled: `is_current=true` → `current`, `is_current=false` → `past`. Onboarding now has a per-course dropdown (Not enrolled / Current / Upcoming / Past) with counts in the header and an "Only show selected" filter. Matching reads from `kind IN ('current','upcoming')` for the buyer and `kind IN ('past','current')` for the seller — `upcoming` sellers don't get credited as having taken the class. Classmates lookup stays on `kind = 'current'` (could be expanded later if useful). New `DELETE /api/me/enrollments/{id}` so the UI can remove an enrollment when the user picks "Not enrolled."
- [x] **User settings page.** New `/settings` page lets users edit their `display_name`. Email is read-only (sourced from Clerk). Backend route `PATCH /api/me`. Solves the "everyone is named 'user'" complaint when paired with the Clerk-side step below.
- [ ] **Configure Clerk JWT template** (manual dashboard step, no code). Clerk dashboard → Configure → Sessions → Edit session token. Add JSON claims `name: "{{user.full_name}}"`, `email: "{{user.primary_email_address}}"`, `picture: "{{user.image_url}}"`. Once saved, existing users' `display_name` and `email` will auto-migrate on next sign-in via the upsert's update branch — no manual data fix needed.
- [ ] **Bronze achieved** — when all of the above are ticked.

### Phase 2: Silver

- [x] **Second nontrivial piece picked: classmates lookup.** Shipped via PR #5 — see "Piece 2 (silver)" above for the design.
- [x] **Unread-message notification badge.** Backend: `GET /api/me/unread-count` and `POST /api/conversations/{id}/read`. Frontend: `useUnreadCount` hook polls every 30s, red badge on the Inbox nav link, Conversation page marks-read on mount. Same polling pattern the gold real-time-chat piece will use (just a shorter interval there).
- [x] **Classmates expansion** (per Sam's ask). Three sub-items, all shipped:
  - **Sort by overlap count, descending** with alphabetical-name tiebreaker.
  - **Show shared course titles under each classmate's name** (e.g. "Intro to Philosophy"), with the code as a small annotation. User asked for names not codes.
  - **Click-to-DM from the Classmates page.** Schema migration `0003`: `conversations.listing_id` is now nullable, plus a new `other_user_id` column (populated from `listing.seller_id` for existing listing convos and from the other party for DMs). New endpoint `POST /api/users/{other_user_id}/dm` is idempotent and canonicalizes the user pair so A→B and B→A return the same row. Frontend: classmate cards are buttons that fire the endpoint and route to `/inbox/<conv_id>`. Inbox + Conversation pages handle the nullable listing.
- [x] **UX restructuring: replace Inbox with per-context chat homes** (per Sam's ask, shipped across PRs #17-#21). Each kind of chat now lives in its semantic home:
  - **`/my-listings`** — seller view. Cards per listing with unread pill; click → Chat subtab (per-buyer threads inline) or Settings subtab (edit fields, replace photo, change status, "Take down" = withdrawn).
  - **`/my-inquiries`** — buyer view. List of listing convos where I'm the buyer; two-pane with inline thread.
  - **`/classmates`** — DM home. List of classmates with per-DM unread badge; click → inline DM thread (creates one if needed).
  - **`/inbox`** top-level removed. `/inbox/:id` kept as back-compat for old shared links.
  - **Nav has three per-context badges** (My listings / My inquiries / Classmates), all sourced from `GET /api/me/unread-counts` (foundation in #17).
  - **Settings polish** (in #21): avatar upload via Supabase Storage at `avatars/<user_id>/...`; placeholder `@clerk.local` email row hidden in the UI.
- [x] **Optimistic updates** on sending a message (PR #22). `<ConversationThread>` adds the message to the list immediately with a temp id + `_pending` flag (dimmed bubble + "Sending…" caption); the POST then swaps the temp for the server message on success, or removes it and restores the input text on failure. Composes cleanly with the real-time polling — if the poll picks up the server-side message between optimistic-add and POST-resolve, the resolve handler dedupes.
- [ ] **Bookmarkable URLs + back button** work end to end. Already mostly true via React Router; verify nothing has broken it during the bronze polish.
- [ ] **Visual design pass** with Tailwind: type scale, color palette, spacing, deliberate components. Not just "works" — looks like someone made choices.
- [ ] **Extra tests for silver behavior** or one e2e-ish test (Playwright) covering sign-up → post listing → message seller.

### Phase 3: Gold

- [ ] **Mobile pass.** Every page works on phone width. No horizontal scrolling. Tap targets ≥ 44px.
- [x] **Pick-one piece: real-time chat via polling** (PR #22). `<ConversationThread>` polls `GET /api/conversations/:id/messages` every 4s while mounted, merges new IDs into the existing list (no re-render of read messages, no scroll jump if the user is reading history). When new incoming messages arrive while the thread is open, the component auto-marks them read and force-refreshes the nav badge. Polling chosen over SSE/WebSockets because the existing chat HTTP endpoint is already the source of truth, Railway's free tier doesn't love long-lived connections, and 4s is imperceptible at this scale.
- [~] **Custom feature 1: image uploads on listings.** Code shipped: migration `0004` adds `listings.image_url`, `app/storage.py` proxies uploads to Supabase Storage, `POST /api/listings/{id}/image` enforces 5 MB cap + JPEG/PNG/WebP MIME + seller-only auth, NewListing form has a file picker, Browse + Detail render the image. **Awaiting one-time manual setup:** in Supabase dashboard create a public-read bucket named `listing-images`, then set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in Railway env vars. Until those are set the endpoint returns 503 ("Image uploads are not configured").
- [ ] **Custom feature 2: general-purpose marketplace ("Everything Else" tab).** Schema: add `category` enum to `listings` (`book`, `furniture`, `electronics`, `clothing`, `sports`, `other`); make book-specific fields nullable for non-book listings. Frontend: new tab on the home page that lists non-book items with category filter + search. The matching feed continues to be books-only.
- [ ] **(Bonus, optional) Seller profile page.** Clickable from any listing — shows the seller's display name, avatar, other active listings, and a "Message me" button. Useful even if it doesn't count toward gold.
- [ ] **README updated** with gold-tier description: both nontrivial pieces (matching + classmates), both custom features (image uploads + general marketplace), and the pick-one (real-time chat).

---

## Note on team spec

The Final Project spec requires 2-3 people. We work sequentially via Claude, but **commits must come from real teammates** for the project to count. Coordinate so every teammate has meaningful commits in `git log` by demo day.
