# UATX_WeChat — Full Project Handoff

> **For future Claude (or any new human contributor):** read this top-to-bottom before doing anything substantial. It's the brain-dump from the prior Claude session that built ~85% of this project. Everything important about the codebase, the infrastructure, the conventions, and the rough edges is here.
>
> If you're going to work in this repo, also read **CLAUDE.md** (working conventions + runway) and **SCHEMA.md** (DB tables in plain English). This file is the long-form complement to those — they're shorter and load into context automatically.

---

## Table of contents

1. [TL;DR](#1-tldr)
2. [The product, in one paragraph](#2-the-product-in-one-paragraph)
3. [Team and ownership](#3-team-and-ownership)
4. [Stack & external services](#4-stack--external-services)
5. [Repo layout](#5-repo-layout)
6. [Data model — every table](#6-data-model--every-table)
7. [Alembic migrations, in order](#7-alembic-migrations-in-order)
8. [Backend endpoints — every one](#8-backend-endpoints--every-one)
9. [Frontend pages & routes](#9-frontend-pages--routes)
10. [Authentication & authorization](#10-authentication--authorization)
11. [The nontrivial logic pieces (spec requirement)](#11-the-nontrivial-logic-pieces-spec-requirement)
12. [Real-time chat](#12-real-time-chat)
13. [Stripe Connect](#13-stripe-connect)
14. [Image uploads](#14-image-uploads)
15. [Wordle](#15-wordle)
16. [Admin tier](#16-admin-tier)
17. [Feature flags](#17-feature-flags)
18. [Rate limiting](#18-rate-limiting)
19. [Environment variables](#19-environment-variables)
20. [Local development setup](#20-local-development-setup)
21. [Tests & CI](#21-tests--ci)
22. [Deployment (Railway + Supabase)](#22-deployment-railway--supabase)
23. [Conventions](#23-conventions)
24. [Common gotchas](#24-common-gotchas)
25. [Decisions log](#25-decisions-log)
26. [PR history (chronological)](#26-pr-history-chronological)
27. [Known issues & quirks](#27-known-issues--quirks)
28. [Future work — features discussed but not built](#28-future-work--features-discussed-but-not-built)
29. [Working with this codebase as Claude](#29-working-with-this-codebase-as-claude)
30. [Quick-start cheatsheet](#30-quick-start-cheatsheet)

---

## 1. TL;DR

- **Project:** UATX_WeChat — a marketplace + chat app for UATX students. Buy/sell textbooks (course-matched) and general items ("Everything Else").
- **Live URL:** https://uatxwechat-production.up.railway.app
- **GitHub:** https://github.com/Sam-Indyk/UATX_WeChat
- **Tier shipped:** Gold (spec satisfied — see `README.md` for the spec mapping).
- **Currently:** in production with ~30–40 real UATX students using it daily.
- **Two-person team:** Sam Indyk (Windows, repo owner, ~51 commits) + Eitan Zarin (macOS, drives Claude, ~42+ commits).
- **Stack:** FastAPI · React/TypeScript/Vite/Tailwind · Postgres (Supabase) · Clerk auth · Railway hosting · Stripe Connect (currently gated off via feature flag).
- **Test count at handoff:** 173 backend (pytest) + 2 frontend (vitest). GitHub Actions runs them on every push, gates Railway deploy on green.

---

## 2. The product, in one paragraph

A web app where UATX students post textbook listings tied to specific courses. The bronze feature is **course-matching**: when a freshman needs the PHIL 101 book, the app surfaces listings from upperclassmen who took PHIL 101, ranked by recency-of-seller-enrollment. Silver adds a **classmates** view (people sharing your current courses). Gold adds **image uploads, a general-purpose "Everything Else" marketplace**, and originally **Stripe Connect** payments (currently UI-disabled via feature flag until we're ready for real-money use). Pick-one: **real-time-ish chat via 4-second polling**. There's also a `/wordle` minigame, a feedback inbox, and admin tooling.

---

## 3. Team and ownership

| Person | Email | OS | Role |
|---|---|---|---|
| **Sam Indyk** | sindyk@student.uaustin.org | Windows | Repo owner. Built initial backend + auth + deploy pipeline. Owned the IA restructuring (PRs #17–#21), real-time chat polling, optimistic message sends, image uploads, the Everything Else marketplace, and the initial mobile + visual passes (PR #28). Performs most merges via GitHub's web UI. |
| **Eitan Zarin** | ezarin@student.uaustin.org | macOS | Drives most agent sessions (this one included). Built course catalog seed (PR #4), classmates lookup (PR #5), classmates expansion (PR #29), Stripe Connect (PR #33), seller-profile page (PR #35), authz safety tests (PR #36), landing-page polish (PR #42), logo + favicon (PR #40), search/sort/freshness/404 polish (PR #46), feedback form (PR #45), Wordle (PR #55), admin tier (PR #59), and the long tail of post-presentation polish. |

**Workflow:** branch-per-PR. Eitan typically asks Claude to push; Sam or Eitan clicks Merge. PR descriptions usually have one-line summaries the team relies on.

**Both admins** (their emails are hardcoded as the default `ADMIN_EMAILS` allowlist — see [Admin tier](#16-admin-tier)).

---

## 4. Stack & external services

| Layer | Choice | Notes |
|---|---|---|
| **Backend framework** | FastAPI 0.119.x | Lots of routers under `backend/app/routers/`. |
| **ORM** | SQLAlchemy 2.x | Imperative `select(...)` style, NOT the legacy query API. |
| **Migrations** | Alembic | Auto-runs on Railway container start. Migration files in `backend/alembic/versions/`. |
| **Database** | Postgres (Supabase managed) in prod; Docker Postgres 16 locally | Direct DB URL via `DATABASE_URL`. We do NOT use Supabase's REST/PostgREST layer — straight Postgres connection. |
| **File storage** | Supabase Storage | One bucket: `listing-images`, configured public-read. Listing photos under `listings/<id>/...`, avatars under `avatars/<user_id>/...`. |
| **Auth** | Clerk (Google sign-in) | App: `related-sunbird-55`. JWT-on-every-request, verified server-side against Clerk's JWKS. NOT Supabase Auth, NOT JWT we issue ourselves. |
| **Payments** | Stripe Connect Express (test mode) | Hosted-checkout redirect flow. Currently UI-disabled via `STRIPE_ENABLED = false` in [frontend/src/lib/feature-flags.ts](frontend/src/lib/feature-flags.ts) — backend code intact. |
| **Frontend framework** | React 18 + TypeScript + Vite | Strict mode TS. |
| **Frontend styling** | Tailwind CSS | Amber-600 is our brand color. |
| **Frontend routing** | react-router-dom 6.30.x | URL params used liberally for bookmarkable state. |
| **Hosting** | Railway | Single service: FastAPI serves the React build at `/` and the API at `/api/*`. One URL, no CORS in prod. Dockerfile + railway.toml at repo root. |
| **Database hosting** | Supabase | Free tier. Project name: `uatx-wechat`. We use ONLY the Postgres DB + Storage. NOT Auth, NOT Realtime, NOT Edge Functions. |
| **CI** | GitHub Actions | `.github/workflows/test.yml` runs pytest + vitest + tsc on every push. Required for merge to main. Railway only deploys when this is green. |
| **Tests** | pytest (backend, 173 tests), Vitest (frontend, 2 tests) | Real Postgres in tests via Docker locally and a Postgres service container in CI — NO SQLite. |

---

## 5. Repo layout

```
/
├── HANDOFF.md                       ← you are here
├── CLAUDE.md                        ← working conventions + runway (auto-loads in agent sessions)
├── README.md                        ← grader-facing project summary
├── SCHEMA.md                        ← data model in plain English
├── EITAN.md                         ← (informal) onboarding notes for Sam → Eitan
├── NEXT_SESSION.md                  ← (informal, untracked-style coordination notes)
├── Dockerfile                       ← Railway build
├── railway.toml                     ← Railway config
├── docker-compose.yml               ← local Postgres
├── .github/workflows/test.yml       ← CI definition
│
├── backend/
│   ├── app/
│   │   ├── main.py                  ← FastAPI app, router registration, static file fallback (SPA)
│   │   ├── config.py                ← Pydantic Settings; reads env vars; defaults for local dev
│   │   ├── db.py                    ← SQLAlchemy engine + Base + get_db dependency
│   │   ├── auth.py                  ← Clerk JWT verification, require_user, get_optional_user, require_admin, is_admin
│   │   ├── rate_limit.py            ← in-memory sliding-window for message sends
│   │   ├── storage.py               ← Supabase Storage upload + delete helpers
│   │   ├── models/                  ← SQLAlchemy models, one file per table
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── course.py            ← Course + Enrollment
│   │   │   ├── listing.py
│   │   │   ├── message.py           ← Conversation + Message
│   │   │   ├── feedback.py          ← FeedbackSubmission
│   │   │   └── wordle.py            ← WordleCompletion
│   │   ├── schemas/
│   │   │   └── common.py            ← ALL Pydantic schemas (request + response models)
│   │   └── routers/
│   │       ├── admin.py             ← /api/admin/* (admin-only)
│   │       ├── classmates.py        ← /api/classmates
│   │       ├── courses.py           ← /api/courses
│   │       ├── feedback.py          ← /api/feedback (user-submitted)
│   │       ├── listings.py          ← /api/listings/*
│   │       ├── matching.py          ← /api/match (still mounted; nav link removed)
│   │       ├── me.py                ← /api/me/* (the signed-in user's own resources)
│   │       ├── messages.py          ← /api/conversations/*, /api/listings/{id}/contact, /api/users/{id}/dm
│   │       ├── stripe_routes.py     ← /api/me/stripe/*, /api/listings/{id}/checkout, /api/stripe/webhook
│   │       ├── users.py             ← /api/users/{id} (public seller profile)
│   │       └── wordle.py            ← /api/wordle/me, /api/wordle/complete
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/                ← migrations 0001 through 0010 (see §7)
│   ├── tests/                       ← pytest tests (~173 at time of handoff)
│   │   ├── conftest.py              ← Shared fixtures (db, make_user, client, anon_client)
│   │   └── test_*.py
│   ├── pyproject.toml               ← pytest config
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── public/
│   │   └── favicon.svg              ← UATX wordmark + wide-W mark, amber-600
│   ├── index.html                   ← Has overflow-x-hidden on <body> as a defense-in-depth
│   ├── src/
│   │   ├── main.tsx                 ← Vite entry; wraps app in <ClerkProvider> + <BrowserRouter>
│   │   ├── App.tsx                  ← All routes + top nav + Clerk SignedIn/SignedOut switching
│   │   ├── components/
│   │   │   ├── ConversationThread.tsx  ← The poll-driven chat thread; optimistic sends
│   │   │   ├── CourseSearchPicker.tsx  ← Searchable combobox for picking a course
│   │   │   ├── Logo.tsx                ← Inlined SVG of the brand mark (currentColor)
│   │   │   └── ListingSettingsForm.tsx ← Edit form on /my-listings/:id
│   │   ├── hooks/
│   │   │   └── useUnreadCount.ts    ← Polls /api/me/unread-counts every 30s; exposes counts.{listings,inquiries,dms,total}
│   │   ├── lib/
│   │   │   ├── api.ts               ← apiRequest (anon) + useApi.request (attaches Clerk JWT)
│   │   │   ├── date.ts              ← formatRelativeDate ("just now" / "12 min ago" / "Jun 4")
│   │   │   ├── feature-flags.ts     ← STRIPE_ENABLED
│   │   │   ├── types.ts             ← All TypeScript types mirroring backend Pydantic schemas
│   │   │   └── wordle.ts            ← WORDLE_WORDS list + scoreGuess() with Wordle dupe-letter rules
│   │   └── pages/                   ← Top-level routed components (see §9)
│   ├── package.json
│   └── vite.config.ts
│
└── (no other significant directories)
```

**One Tailwind note:** the body has `overflow-x-hidden` (see [frontend/index.html](frontend/index.html)) as a defense-in-depth against horizontal-scroll regressions. PR #48 added it.

---

## 6. Data model — every table

Postgres conventions: snake_case, real foreign keys, `NOT NULL` by default, every table has `created_at TIMESTAMPTZ DEFAULT now()`, UUIDs for PKs **except** `users.id` (which is the Clerk user ID string, like `user_2abc...`).

### `users`
- `id` — TEXT primary key. **This is the Clerk user ID string.** Not a UUID. Means JWT-to-DB lookup is a single PK SELECT.
- `email` — TEXT UNIQUE NOT NULL. From the Clerk JWT's `email` claim, or synthesized `<sub>@clerk.local` if Clerk's JWT template hasn't been configured.
- `display_name` — TEXT NOT NULL. From Clerk's `name` claim, or fallback `"User <last-6-of-sub>"`.
- `avatar_url` — TEXT nullable. From Clerk's `picture` claim, OR a Supabase Storage URL if the user uploaded their own via `/settings`.
- `stripe_account_id` — VARCHAR(64) UNIQUE nullable. Set when the user starts Stripe Connect onboarding.
- `stripe_onboarded` — BOOLEAN NOT NULL DEFAULT false. Flipped to true by the `account.updated` webhook when `charges_enabled` AND `details_submitted` are both true.
- `created_at`

### `courses`
- `id` — UUID PK
- `code` — TEXT NOT NULL (e.g., "PHIL 101")
- `title` — TEXT NOT NULL (e.g., "Intro to Philosophy")
- `created_at`
- **167 rows seeded** from the 2025-26 UATX catalog via migration `0002_seed_courses.py`. Idempotent (`ON CONFLICT DO NOTHING`).

### `enrollments`
- `id` — UUID PK
- `user_id` — TEXT FK → `users.id` ON DELETE CASCADE
- `course_id` — UUID FK → `courses.id` ON DELETE RESTRICT
- `term` — TEXT NOT NULL (e.g., "Spring 2026")
- `kind` — TEXT NOT NULL, CHECK in `('past', 'current', 'upcoming')`. Added in migration 0005 (replaced an earlier `is_current` BOOLEAN).
- `created_at`
- The matching algorithm reads `kind IN ('current','upcoming')` for the buyer's relevant courses; the classmates query spans all three kinds on both sides (see §11).

### `listings`
- `id` — UUID PK
- `seller_id` — TEXT FK → `users.id` ON DELETE CASCADE
- `course_id` — UUID FK → `courses.id` ON DELETE SET NULL. Nullable for non-book listings.
- `category` — TEXT NOT NULL, CHECK in `('book', 'furniture', 'electronics', 'clothing', 'kitchen', 'decor', 'sports', 'transportation', 'other')`. Default `'book'`.
- `title` — TEXT NOT NULL (max 200). Renamed from `book_title` in migration 0006.
- `author` — TEXT nullable, max 200. (Was required for books pre-PR-#38; now optional.) Renamed from `book_author`.
- `edition` — TEXT nullable, max 40. Renamed from `book_edition`.
- `condition` — TEXT NOT NULL, CHECK in `('new', 'like_new', 'good', 'fair', 'poor')`.
- `price_cents` — INT NOT NULL, CHECK >= 0. Capped server-side at 10_000_000 (= $100K) via Pydantic. See PR #50 — without the cap, large typos overflowed INT4 and gave 500s.
- `description` — TEXT NOT NULL DEFAULT '', max 2000.
- `status` — TEXT NOT NULL, CHECK in `('active', 'reserved', 'sold', 'withdrawn')`. Default `'active'`.
- `image_url` — TEXT nullable. Supabase Storage public URL.
- `payment_methods` — TEXT[] NOT NULL DEFAULT '{}'. Postgres ARRAY column. Allowed values: `cash`, `venmo`, `zelle`, `paypal`, `stripe`.
- `created_at`
- `updated_at` — TIMESTAMPTZ.

### `conversations`
- `id` — UUID PK
- `listing_id` — UUID FK → `listings.id` ON DELETE CASCADE. **Nullable** — null means it's a direct message (not tied to a specific listing).
- `buyer_id` — TEXT FK → `users.id` ON DELETE CASCADE.
- `other_user_id` — TEXT FK → `users.id` ON DELETE CASCADE. For listing chats this equals `listings.seller_id` (denormalized to make per-context unread queries fast). For DMs it's the other party.
- `created_at`
- `updated_at`
- **DM canonicalization:** when a user starts a DM via `POST /api/users/{other_id}/dm`, we sort the two user IDs alphabetically and store the smaller as `buyer_id`. This means A→B and B→A always return the same row.

### `messages`
- `id` — UUID PK
- `conversation_id` — UUID FK → `conversations.id` ON DELETE CASCADE
- `sender_id` — TEXT FK → `users.id` ON DELETE CASCADE
- `body` — TEXT NOT NULL (1 ≤ length ≤ 2000)
- `created_at`
- `read_at` — TIMESTAMPTZ nullable. Set by `POST /api/conversations/{id}/read` for incoming messages to mark them read. Drives the unread badges.

### `feedback_submissions`
- `id` — UUID PK
- `user_id` — TEXT FK → `users.id` ON DELETE SET NULL. (NULL so feedback survives author deletion.)
- `category` — TEXT NOT NULL, CHECK in `('feature', 'bug', 'other')`.
- `body` — TEXT NOT NULL (1 ≤ length ≤ 4000)
- `created_at`
- Indexed on `created_at` for the admin inbox.

### `wordle_completions`
- `id` — UUID PK
- `user_id` — TEXT FK → `users.id` ON DELETE CASCADE
- `game_index` — INT NOT NULL, CHECK >= 0. References position in the frontend `WORDLE_WORDS` array (backend doesn't know the words themselves).
- `num_guesses` — INT NOT NULL, CHECK >= 1.
- `created_at`
- UNIQUE (`user_id`, `game_index`). Endpoint upserts and keeps the BEST attempt (fewest guesses).
- Wins only — no row means not yet won.

---

## 7. Alembic migrations, in order

| # | File | What it does |
|---|---|---|
| 0001 | `0001_initial.py` | Base schema: users, courses, enrollments (with `is_current` bool), listings (with `book_*` columns), conversations (listing-scoped only), messages. |
| 0002 | `0002_seed_courses.py` | Data migration: inserts the 167 UATX courses with ON CONFLICT DO NOTHING. |
| 0003 | `0003_conversations_allow_dms.py` | `conversations.listing_id` nullable + new `other_user_id` column. Enables DMs (Classmates page). |
| 0004 | `0004_listing_image_url.py` | Adds `listings.image_url`. |
| 0005 | `0005_enrollment_kind.py` | Drops `enrollments.is_current`, adds `kind` CHECK constraint. Backfills: `is_current=true → 'current'`, `false → 'past'`. |
| 0006 | `0006_marketplace_categories.py` | Renames `book_title/author/edition` → `title/author/edition`. Makes `author` nullable. Adds `category` CHECK column. Backfills existing rows as `'book'`. |
| 0007 | `0007_listing_payment_methods.py` | Adds `listings.payment_methods` TEXT[] column. |
| 0008 | `0008_user_stripe_fields.py` | Adds `users.stripe_account_id` (UNIQUE nullable) and `users.stripe_onboarded` (BOOL default false). |
| 0009 | `0009_feedback_submissions.py` | Creates `feedback_submissions` table. |
| 0010 | `0010_wordle_completions.py` | Creates `wordle_completions` table. |

**Migrations auto-run** on every Railway container start via the Dockerfile (`alembic upgrade head` before launching uvicorn).

---

## 8. Backend endpoints — every one

Every route is rooted at `/api/`. Auth requirements noted per row.

### `app/routers/me.py` — the signed-in user's own resources

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/me` | required | Returns the signed-in user. Also stamps `is_admin: bool` computed from the email allowlist. |
| PATCH | `/api/me` | required | Update display_name. (Email comes from Clerk, not editable.) |
| POST | `/api/me/avatar` | required | Upload avatar to Supabase Storage. 5 MB cap, JPEG/PNG/WebP. |
| GET | `/api/me/enrollments` | required | List my enrollments ordered current → upcoming → past, then by term desc. |
| POST | `/api/me/enrollments` | required | Upsert an enrollment for a (course, term) — used by `/my-classes`. |
| DELETE | `/api/me/enrollments/{id}` | required | Remove an enrollment. |
| GET | `/api/me/unread-count` | required | Total incoming unread messages across all my conversations. |
| GET | `/api/me/unread-counts` | required | Per-context breakdown: `{listings, inquiries, dms, total}`. ONE batched query with three SUM(CASE) clauses. Drives the three nav badges. |
| POST | `/api/conversations/{id}/read` | required | Mark all incoming messages in a conversation as read. |
| GET | `/api/me/listings` | required | My posted listings (excluding `withdrawn`), with per-listing `unread_count`. |
| GET | `/api/me/inquiries` | required | Listing conversations where I'm the buyer (per-conv unread). |

### `app/routers/courses.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/courses` | none | List all courses. Used by every course picker. |

### `app/routers/listings.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/listings` | optional | Browse listings. Query params: `category` (`book` / `non-book` / specific), `course_id`, `q` (case-insensitive title+author search, LIKE wildcards escaped), `status` (default `active`), `my_courses` (true → filter to my current/upcoming enrollments; **requires auth**). |
| GET | `/api/listings/{id}` | none | Single listing detail. |
| POST | `/api/listings` | required | Create. Books may now omit author (PR #38). Price capped server-side at $100K. |
| PATCH | `/api/listings/{id}` | required + seller-only (403 otherwise) | Update. Supports partial updates (only fields sent are applied). |
| DELETE | `/api/listings/{id}` | required + seller-only | **Hard-deletes** the listing. FK cascades remove conversations + messages. Best-effort deletes the Supabase Storage photo. |
| POST | `/api/listings/{id}/image` | required + seller-only | Upload listing photo to Supabase Storage. 5 MB / MIME-restricted. |
| GET | `/api/listings/{id}/conversations` | required + seller-only | All conversations on this listing (seller's chat subtab). |

### `app/routers/messages.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/listings/{id}/contact` | required | Buyer starts/resumes a conversation about a listing. 400 if you're the seller. Idempotent on (buyer, listing). |
| POST | `/api/users/{other_id}/dm` | required | Start/resume a DM (no listing context). 400 on self-DM, 404 if user not found. Idempotent via canonicalization. |
| GET | `/api/conversations` | required | All my conversations (listing chats + DMs), per-conv unread count. |
| GET | `/api/conversations/{id}/messages` | required + membership-only | List messages. 403 if not in the conversation. |
| POST | `/api/conversations/{id}/messages` | required + membership-only + rate-limited | Send a message. **30 per 60s per user** — returns 429 with Retry-After. Bumps `conversations.updated_at`. |

### `app/routers/matching.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/match` | required | Course-matching algorithm. **Bronze nontrivial logic.** See §11. |

### `app/routers/classmates.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/classmates` | required | Classmates lookup. **Silver nontrivial logic.** See §11. Returns each classmate with their `shared_courses` (each carries the OTHER user's `kind` for UI color-coding) and `dm_conversation_id` + `unread_count`. |

### `app/routers/users.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/users/{user_id}` | required | Public seller profile: id, display_name, avatar_url + `active_listings`. Deliberately excludes email + `stripe_onboarded`. |

### `app/routers/stripe_routes.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/me/stripe/onboard` | required | Create (or reuse) a Stripe Connect Express account; generate an account-link; return `{onboarding_url}`. 503 if `STRIPE_SECRET_KEY` unset. |
| POST | `/api/listings/{id}/checkout` | required | Create a hosted Checkout Session for a listing. Destination charge to the seller's connected account. 400 if buying own listing, 400 if listing isn't active, 400 if seller hasn't enabled Stripe or finished onboarding. |
| POST | `/api/stripe/webhook` | signature-verified | Stripe → us. Verifies signature with `STRIPE_WEBHOOK_SECRET`. Handles `account.updated` (flips `stripe_onboarded`) and `checkout.session.completed` (sets listing → `reserved`). Idempotent. |

### `app/routers/feedback.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/feedback` | required | User submits feedback. Body validated: category in (feature/bug/other), body 1-4000 chars. |

### `app/routers/admin.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/admin/feedback` | required + admin-only | All feedback submissions joined with submitter info. 403 if caller isn't in `ADMIN_EMAILS` allowlist. |

### `app/routers/wordle.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/wordle/me` | required | My Wordle completions. |
| POST | `/api/wordle/complete` | required | Record a win. Upserts on `(user_id, game_index)` keeping fewest guesses. |

### Health
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | none | Returns `{"status":"ok"}`. Used as a smoke test on the live URL. |

---

## 9. Frontend pages & routes

All defined in [frontend/src/App.tsx](frontend/src/App.tsx). `RequireAuth` wrapper redirects to `/sign-in` if unauthenticated; `SignedIn` / `SignedOut` Clerk components toggle in-page UI.

| Route | Component | Auth | Purpose |
|---|---|---|---|
| `/` | `Home.tsx` | none | Landing page. Hero (logo + headline + 3 amber CTAs). Three feature cards. Footer credit. |
| `/sign-in/*` | Clerk's `<SignIn>` | none | Sign-in flow. |
| `/listings` | `Listings.tsx` | none | Books browse. Filters: search (`?q=`), course (`?course_id=`), sort (`?sort=`), "My courses" toggle (`?mine=1`, signed-in only). Cards show title, author, course code, price, condition, "by Seller · Posted X ago". |
| `/listings/new` | `NewListing.tsx` | required | Post a book listing. Author optional. Price input is text+numeric, capped at $100K. Stripe checkbox grayed-out via feature flag. |
| `/listings/:id` | `ListingDetail.tsx` | none (signed-in features gated) | Listing detail. Course code + "You're in this class now/past/upcoming" chip (if enrolled). Pay-with-Stripe button (gated). Message-seller button. Photo. "More from this seller" preview. Self-view shows "Manage in My listings" link. |
| `/everything-else` | `EverythingElse.tsx` | none | Non-book marketplace. Category filter, search. Image-heavy card grid. |
| `/everything-else/new` | `NewItem.tsx` | required | Post a non-book item. Photo required. Same Stripe gating. |
| `/my-classes` | `MyClasses.tsx` | required | Course-enrollment manager. Search + filter UI over the 167 courses. Per-course dropdown: Not enrolled / Current / Upcoming / Past. |
| `/match` | `Match.tsx` | required | Course matches. **No longer linked from the nav** (PR #60 replaced with the "My courses" filter on `/listings`). Still mounted as back-compat. |
| `/classmates` | `Classmates.tsx` | required | Two-pane layout: classmate list (left), inline DM thread (right). Each classmate row shows shared courses with color-coded kind chips. ?dm= persists the open thread. |
| `/inbox/:id` | `Conversation.tsx` | required | Back-compat — listing chats now live in `/my-listings` and DMs in `/classmates`. Old shared links still work. |
| `/my-listings` | `MyListings.tsx` | required | Seller's view. Books / Everything Else tabs (`?tab=`). Header has BOTH "+ Sell a book" and "+ Sell something else" amber buttons. Per-listing unread badges. |
| `/my-listings/:id` | `MyListingDetail.tsx` | required | Two subtabs: Chat (per-buyer threads inline) and Settings (edit fields, replace photo, change status, Take down = hard-delete). |
| `/my-inquiries` | `MyInquiries.tsx` | required | Buyer's view. Listing conversations where I'm the buyer. Two-pane with inline thread. |
| `/users/:userId` | `UserProfile.tsx` | required | Public seller profile. Avatar + display name + active listings grid + "Message me" button. Self-view shows "Manage your listings →" instead. |
| `/settings` | `Settings.tsx` | required | Edit display name, upload avatar. Stripe section (grayed-out per feature flag). Conditional Admin section (only for admins) linking to `/admin/feedback`. Feedback link. |
| `/feedback` | `Feedback.tsx` | required | User-feedback form (category dropdown + textarea). |
| `/admin/feedback` | `AdminFeedback.tsx` | required + admin (checks via `/api/me`'s is_admin field) | Lists all feedback submissions. Non-admins see a friendly "Not an admin" page. |
| `/wordle` | `WordleHub.tsx` | required | Wordle game list (20 games), with per-game win status. |
| `/wordle/:gameIndex` | `WordleGame.tsx` | required | Plays an individual game. Wordle-classic with proper duplicate-letter scoring. |
| `*` | `NotFound.tsx` | none | Catch-all 404 page with logo + back-home + browse-books links. |

**Nav (top of every page)** — [App.tsx](frontend/src/App.tsx):
- Logo + "UATX_WeChat"
- (always) Books · Everything else
- (signed in) My classes · Classmates · My listings · My inquiries · Wordle · (right side) Settings · Clerk avatar
- Hamburger menu below `md` breakpoint; everything except brand + avatar collapses into a slide-down menu.

---

## 10. Authentication & authorization

### Clerk JWT verification
Lives in [`backend/app/auth.py`](backend/app/auth.py).

1. Frontend attaches `Authorization: Bearer <clerk-jwt>` to every API request (via `useApi.request`).
2. Backend `require_user` dependency:
   - Reads the header. 401 if missing.
   - Fetches Clerk's JWKS from `CLERK_JWKS_URL`. Cached in-process for **1 hour**.
   - Verifies the JWT signature (RS256) against the matching public key.
   - Extracts `sub` claim — this is the Clerk user ID, like `user_2abc...`.
   - **Upserts** the user row. Pulls `email`, `name`, `picture` from the JWT if Clerk's session-token template has those claims configured; otherwise synthesizes `<sub>@clerk.local` for the email so the UNIQUE constraint doesn't collide for new users.
   - Returns the SQLAlchemy `User` instance.
3. `get_optional_user` (PR #60 + PR #61 perf fix): like `require_user` but returns `None` for unauthenticated calls and **does NOT upsert/commit/refresh** — just JWT verify + a single PK SELECT. Used on `/api/listings` so signed-in browsing doesn't pay an upsert cost on every hit. Will return `None` for a user that doesn't yet have a row (treated as anon); in practice `/api/me` runs on app boot and creates rows.
4. `require_admin`: like `require_user` but additionally checks `user.email` against `ADMIN_EMAILS` allowlist; 403 if not present.
5. `is_admin(user)`: bool helper used by `/api/me` to stamp the `is_admin` field in the response.

### Domain allowlist
`ALLOWED_EMAIL_DOMAINS` env var. **Defaults to empty (open to all domains).** If set, comma-separated. When non-empty, `_enforce_email_domain()` raises 403 if the user's email doesn't match.

The default was previously `"student.uaustin.org"` which silently locked prod out for non-UATX accounts the moment the Clerk JWT template started providing real emails. Fixed in PR #34. **Now defaults to empty.** Set explicitly via Railway env var if you want to restrict.

For UATX-wide launch: set `ALLOWED_EMAIL_DOMAINS=student.uaustin.org,uaustin.org` on Railway as defense-in-depth alongside Clerk's signup-domain restriction.

### Admin allowlist
`ADMIN_EMAILS` env var with default `"ezarin@student.uaustin.org,sindyk@student.uaustin.org"`. Comma-separated, case-insensitive. Override on Railway if needed.

### Test overrides
[backend/tests/conftest.py](backend/tests/conftest.py) overrides BOTH `require_user` and `get_optional_user` via `app.dependency_overrides` to return the test's `current_user`. `anon_client` doesn't override (so the real implementations run, return None / 401 for missing headers). `client.set_user(user)` swaps the current user mid-test.

---

## 11. The nontrivial logic pieces (spec requirement)

### Bronze: course-matching algorithm
[backend/app/routers/matching.py](backend/app/routers/matching.py) → `match_listings_for_user`.

For the signed-in user:
1. Read enrollments where `kind IN ('current', 'upcoming')` — the courses the buyer might need books for.
2. Find active book listings whose `course_id` is in that set.
3. Exclude the user's own listings.
4. Rank by:
   - **Primary:** seller's "course recency" — how recently the seller was enrolled in the same course. Sellers whose enrollment is `kind='current'` outrank `'past'`; among `past`, more-recent terms (alphabetically/lexically newer) rank higher.
   - **Tiebreaker 1:** listing freshness (newer `created_at` first).
   - **Tiebreaker 2:** lower `price_cents` first.
5. Return ranked list with seller's display name and a rationale string ("Seller took PHIL 101 in Fall 2024").

Edge cases handled: user with no current/upcoming enrollments → empty; no listings match → empty; all matches are the user's own → excluded by the where clause.

### Silver: classmates lookup
[backend/app/routers/classmates.py](backend/app/routers/classmates.py) → `list_classmates`.

For the signed-in user:
1. Get all course IDs the user has any enrollment in (any kind: past/current/upcoming). Distinct.
2. Find other users (`User.id != viewer.id`) enrolled in any of those courses (any kind).
3. Group per other user. Each shared course is returned with the OTHER user's `kind` for that course.
4. Dedup: a classmate who took the same course in multiple terms (retake) appears once with the highest-priority kind (current > past > upcoming).
5. Sort by overlap count desc, then alphabetical name as a stable tiebreaker.
6. Annotate each classmate row with `dm_conversation_id` (null if no DM exists) and `unread_count` (incoming messages in that DM the viewer hasn't read).

Originally only viewer's `kind='current'` counted — PR #29 expanded to all kinds on the viewer's side to match the spec ("anyone I share any class with").

---

## 12. Real-time chat

**Pick-one Gold piece.** [frontend/src/components/ConversationThread.tsx](frontend/src/components/ConversationThread.tsx).

Mechanics:
- While the component is mounted, `setInterval` calls `GET /api/conversations/:id/messages` every **4 seconds**.
- New message IDs are merged into the existing list (no re-render of read messages; no scroll-jump if the user is scrolled up reading history).
- Auto-scroll only fires when the user is at (or within 80px of) the bottom.
- When new incoming messages arrive while the thread is open, the component fires `POST /api/conversations/:id/read` to mark them read, then forces a `useUnread.refetch()` so the nav badge drops immediately.
- Spec ceiling is 5s end-to-end; 4s is comfortably under.

Optimistic sends:
- Click Send → immediately appends a message with a temp ID + `_pending: true` flag (dimmed bubble + "Sending…" caption).
- `POST` follows. On success: replace the temp with the server's confirmed message. If the polling tick had already pulled the server version mid-flight, the replace handler dedupes.
- On failure: remove the optimistic bubble and restore the typed text in the input.

**Rate limit:** 30 sends per 60s per user (sliding window). See §18.

**Why polling over WebSockets:** the HTTP endpoint is already the source of truth. WebSockets need parallel transport, server-side connection bookkeeping, and a sticky-session-friendly host. Railway's free tier doesn't love long-lived connections. Polling composes with the existing `useUnread` 30s pattern. See PR #22 + README for the full rationale.

---

## 13. Stripe Connect

[backend/app/routers/stripe_routes.py](backend/app/routers/stripe_routes.py) + [frontend/src/pages/Settings.tsx](frontend/src/pages/Settings.tsx) (onboarding) + [frontend/src/pages/ListingDetail.tsx](frontend/src/pages/ListingDetail.tsx) (Pay with Stripe button).

**Currently UI-disabled** via `STRIPE_ENABLED = false` in [frontend/src/lib/feature-flags.ts](frontend/src/lib/feature-flags.ts). Backend code intact. To re-enable, flip the flag and ensure `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` are set on Railway.

### Onboarding flow
1. Seller clicks "Connect with Stripe" in `/settings`.
2. Backend creates a Stripe Connect Express account on their behalf (if no `stripe_account_id` exists yet), then generates a fresh `AccountLink`.
3. Browser redirects to Stripe's hosted onboarding form.
4. After completion, Stripe redirects back to `STRIPE_RETURN_URL_BASE/settings?stripe=return`.
5. Stripe also sends an `account.updated` webhook. We verify the signature, check `charges_enabled && details_submitted`, flip `users.stripe_onboarded = true`.
6. The green "Connected" pill appears on `/settings` after the next page load.

### Purchase flow
1. Buyer sees "Pay with Stripe" on a listing when: seller has `payment_methods` containing `stripe` AND `seller.stripe_onboarded == true` AND listing.status == active AND viewer != seller.
2. Click → backend creates a Stripe Checkout Session as a **destination charge** (funds route to the seller's connected account, optional platform fee via `STRIPE_PLATFORM_FEE_BPS`).
3. Browser hard-redirects to Stripe's hosted checkout page.
4. After payment: redirect back to `/listings/{id}?stripe=success` (or `?stripe=cancel`).
5. Stripe sends `checkout.session.completed` webhook. We verify signature, parse the metadata's `listing_id`, flip `listing.status = 'reserved'` if it's still `active`.

### Test mode notes
- Card: `4242 4242 4242 4242`, any future exp, any CVC, any ZIP.
- For Stripe's hosted onboarding form, use dummy values per https://docs.stripe.com/connect/testing — SSN `0000`, routing `110000000`, account `000123456789`, phone `000-000-0000`.
- **Critical gotcha:** if a Connect-onboarding seller has the SAME email as the Stripe Dashboard account owner, Stripe rejects the onboarding (you can't be both platform owner and a connected seller with one email). Use a different email for testing. Took us 15 minutes to figure out the first time.

### Why Checkout-redirect over embedded Elements
Stripe hosts the entire payment UI → zero PCI scope on our end. Tradeoff is one extra redirect, but the code savings are massive (no Elements provider, no PaymentIntent client-secret state machine, no card-field handling).

### Local webhook testing
```bash
brew install stripe/stripe-cli/stripe
stripe login
stripe listen --forward-to localhost:8000/api/stripe/webhook
# Copy the printed whsec_... into backend/.env as STRIPE_WEBHOOK_SECRET.
```

The 17 backend Stripe tests use `monkeypatch` to mock the SDK, including a `stripe_unconfigured` fixture for the 503-when-unconfigured branch.

---

## 14. Image uploads

[backend/app/storage.py](backend/app/storage.py).

- Supabase Storage bucket `listing-images`, configured public-read.
- Path conventions: `listings/<listing_id>/<random_uuid>.<ext>` for listing photos, `avatars/<user_id>/<random_uuid>.<ext>` for avatars. **UUIDs in paths, not user input** → no path traversal.
- Backend validates: MIME in `{image/jpeg, image/png, image/webp}` and size ≤ 5 MB. Validation happens both at the router (so we don't read the whole upload into memory unnecessarily) AND inside `storage.py` (belt-and-suspenders).
- Returns the Supabase Storage public URL. Backend stores that URL in `listings.image_url` / `users.avatar_url`.
- When a listing is hard-deleted (Take down), `delete_stored_image` best-effort removes the photo from Storage. Silent on failure — an orphaned object is a space leak, not a correctness bug.
- 503 when `SUPABASE_URL` or `SUPABASE_SERVICE_KEY` is empty.

---

## 15. Wordle

[backend/app/routers/wordle.py](backend/app/routers/wordle.py) + [frontend/src/lib/wordle.ts](frontend/src/lib/wordle.ts) + [frontend/src/pages/WordleHub.tsx](frontend/src/pages/WordleHub.tsx) + [frontend/src/pages/WordleGame.tsx](frontend/src/pages/WordleGame.tsx).

- 20 UATX-themed words. Word list lives ONLY on the frontend (`WORDLE_WORDS`). Backend doesn't know the words — it just persists `(user_id, game_index, num_guesses)`.
- Variable word length. Guess cap is `max(6, word.length)` so short words get classic Wordle (6 guesses), long words get more room.
- Color rules with **proper duplicate-letter handling**: two-pass scoring. First mark greens (exact-position matches), removing those answer letters from the remaining pool. Then mark yellows only if the remaining pool still has an unmatched copy of that letter.
- `POST /api/wordle/complete` is upsert on `(user_id, game_index)` — keeps the BEST attempt (fewest guesses).
- Per-user privacy: `GET /api/wordle/me` returns only the caller's completions. No leaderboard.

---

## 16. Admin tier

[backend/app/routers/admin.py](backend/app/routers/admin.py) + [frontend/src/pages/AdminFeedback.tsx](frontend/src/pages/AdminFeedback.tsx).

- `ADMIN_EMAILS` env var (default: `ezarin@student.uaustin.org,sindyk@student.uaustin.org`). Comma-separated.
- `is_admin(user)` and `require_admin` in `auth.py`.
- `GET /api/me` stamps `is_admin: bool` so the frontend can conditionally show admin UI. Other `UserOut` responses keep `is_admin: false` (no leakage).
- `/admin/feedback` route + Settings page conditional link (only shown to admins). Non-admins visiting the URL directly see a friendly "Not an admin" page (not a 403 error UI).
- Only endpoint so far: `GET /api/admin/feedback` returning all submissions joined with the submitter (LEFT JOIN, so deleted-author rows still appear with null user info).

---

## 17. Feature flags

[frontend/src/lib/feature-flags.ts](frontend/src/lib/feature-flags.ts).

Currently:
- `STRIPE_ENABLED = false` — controls whether the Stripe Connect UI is shown. When false:
  - "Stripe" checkbox on New Listing + New Item forms is grayed out with a "Coming soon" badge.
  - "Connect with Stripe" button in Settings is grayed out with an explainer.
  - "Pay with Stripe" button on listing detail is intentionally NOT gated — legacy listings whose sellers already onboarded keep working. We don't break in-flight transactions.
  - **All backend code stays.** Flipping back to true restores everything.

Add new flags here as needed. They're build-time constants — Vite bakes them into the bundle. To toggle without a code change, you'd need to make them env-driven (`VITE_*` env vars).

---

## 18. Rate limiting

[backend/app/rate_limit.py](backend/app/rate_limit.py).

- **30 messages per 60-second sliding window, per user.** Applied to `POST /api/conversations/{id}/messages` only.
- In-memory dict of `deque[float]` keyed by `user_id`. `threading.Lock` for concurrent-request safety within a single uvicorn worker.
- User-id keying, NOT IP. Dorm networks share NATs — IP keying would punish bystanders when one student misbehaves.
- Single Railway container → in-process state is fine. Container restart resets the window (acceptable; the goal is UX, not security).
- Returns 429 with `Retry-After` header on violation.
- `reset_for_tests()` cleared from conftest before each test so state doesn't leak across tests.
- Added in PR #52 after a real flood incident from "Pierce Crist" (a classmate testing the limits).

---

## 19. Environment variables

Set in `backend/.env` locally (gitignored) and on Railway's Variables tab in production. See [backend/.env.example](backend/.env.example) for the canonical list.

| Var | Required? | Default in code | What it does |
|---|---|---|---|
| `DATABASE_URL` | yes (prod) | local Docker URL | Postgres connection string. Railway gets this from the linked Supabase project. |
| `CLERK_JWKS_URL` | yes | (empty) | URL to fetch Clerk's public keys. Set to `https://<clerk-app>.clerk.accounts.dev/.well-known/jwks.json`. |
| `CLERK_ISSUER` | yes | (empty) | Expected `iss` claim on JWTs (= the same Clerk URL minus the JWKS path). |
| `CLERK_AUDIENCE` | optional | (empty) | If set, validates the `aud` claim. We leave it empty. |
| `ALLOWED_EMAIL_DOMAINS` | optional | `""` (empty = open) | Comma-separated allowed email domains. Empty means all. Defaults to empty after PR #34 fixed a silent prod 403 bug. |
| `APP_ENV` | optional | `dev` | Switches CORS middleware on in dev (allows `http://localhost:5173`). Prod sets it to `prod`. |
| `SUPABASE_URL` | yes (for uploads) | (empty) | Supabase project URL. |
| `SUPABASE_SERVICE_KEY` | yes (for uploads) | (empty) | Service-role key (DO NOT EXPOSE TO FRONTEND). Backend uses this to upload to Storage. |
| `SUPABASE_STORAGE_BUCKET` | optional | `"listing-images"` | Bucket name. We use one bucket for both listings + avatars. |
| `STRIPE_SECRET_KEY` | required for Stripe | (empty) | `sk_test_...` or `sk_live_...`. Empty → all Stripe endpoints return 503. |
| `STRIPE_WEBHOOK_SECRET` | required for webhooks | (empty) | `whsec_...`. Used to verify webhook signatures. |
| `STRIPE_RETURN_URL_BASE` | required for Stripe | `http://localhost:5173` | Where Stripe redirects after checkout / onboarding. In prod set to the Railway URL. |
| `STRIPE_PLATFORM_FEE_BPS` | optional | `0` | Basis points (1 bp = 0.01%) the platform skims from each checkout. Demo uses 0. **Must be an integer** — letter `o` instead of digit `0` will crash the container at startup (real Railway typo, took us 30 min to diagnose). |
| `ADMIN_EMAILS` | optional | `ezarin@student.uaustin.org,sindyk@student.uaustin.org` | Comma-separated admin email allowlist. |

**Frontend env (Vite):**
| Var | Required? | What it does |
|---|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | yes | Clerk's publishable key (`pk_test_...`). Different from the secret key; this is safe to ship in the JS bundle. |
| `VITE_API_URL` | yes (dev) | Backend URL. `http://localhost:8000` for local; in prod we leave it unset/empty and let same-origin take over. |

---

## 20. Local development setup

```bash
# Prereqs: Python 3.12, Node 20+, Docker Desktop.

# 1. Postgres
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # macOS/linux
# .venv\Scripts\activate           # Windows
pip install -r requirements.txt
cp .env.example .env                # then fill in CLERK_* and SUPABASE_* values
alembic upgrade head
uvicorn app.main:app --reload       # binds http://localhost:8000

# 3. Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env                # then fill in VITE_CLERK_PUBLISHABLE_KEY
npm run dev                         # opens http://localhost:5173
```

**For Stripe local dev:**
```bash
brew install stripe/stripe-cli/stripe
stripe login
stripe listen --forward-to localhost:8000/api/stripe/webhook
# Copy printed whsec_... into backend/.env as STRIPE_WEBHOOK_SECRET
```

**Visit http://localhost:5173.** API docs are at http://localhost:8000/docs (Swagger UI). Health at http://localhost:8000/api/health.

**Common local-dev gotchas:**
- The frontend dev server (Vite) listens on 5173 and proxies API calls to `:8000`. CORS is enabled only when `APP_ENV=dev` in the backend.
- If Docker Postgres is stopped or unhealthy, the backend crashes on startup with a connection error. Fix: `docker compose up -d`.
- If your local Clerk JWT doesn't include the email claim (default Clerk session token doesn't), users get `<sub>@clerk.local` synthesized as their email. To fix: configure Clerk's session-token template to include `email: {{user.primary_email_address}}`, `name: {{user.full_name}}`, `picture: {{user.image_url}}`. **This is a manual Clerk dashboard step.** Once done, sign out and back in to refresh.

---

## 21. Tests & CI

**Backend (~173 tests):** pytest in `backend/tests/`. Each test independent — `db` fixture TRUNCATEs all data before yielding. Auth bypassed via `app.dependency_overrides` (no real JWT verification in tests).

**Frontend (2 tests):** Vitest in `frontend/src/lib/api.test.ts`. Mostly covers the api helper.

**CI:** [.github/workflows/test.yml](.github/workflows/test.yml). On every push to `main` (and PRs):
1. Spin up a Postgres service container.
2. Backend: `pip install -r requirements.txt && pytest`.
3. Frontend: `npm install && npm run lint && npx tsc --noEmit && npx vitest run`.
4. If anything fails, the deploy is blocked.

**Railway deploy** is gated on green CI: the Railway integration only deploys commits where `main`'s CI passed.

**Conftest patterns** worth knowing:
- `db` fixture: per-test, TRUNCATEs everything (`wordle_completions, feedback_submissions, messages, conversations, listings, enrollments, courses, users RESTART IDENTITY CASCADE`) + calls `reset_for_tests()` to clear the in-memory rate limiter.
- `make_user(email=..., display_name=...)`: factory for User rows.
- `client`: TestClient with `require_user` and `get_optional_user` both overridden to return `current_user`. `client.set_user(other)` swaps the current user.
- `anon_client`: no overrides — exercises the real auth path so we test 401s.

**Test conventions:**
- Use real Postgres (Docker locally, Postgres service container in CI). NEVER mock the DB. This is a CLAUDE.md hard rule.
- Cover happy path + at least one edge case for every nontrivial endpoint.
- For external services (Stripe SDK, Supabase Storage), use `monkeypatch.setattr` to swap with `SimpleNamespace` doubles. See [test_stripe.py](backend/tests/test_stripe.py) for the pattern.

**The 173 tests cover:**
- All routers (auth, listings, messages, conversations, classmates, matching, me, courses, feedback, users, wordle, admin, stripe).
- Cross-user authz boundaries (PR #36's `test_authz_safety.py`).
- Rate-limit boundary cases.
- Search wildcard escaping.
- Payment-method validation + price-cap validation.

---

## 22. Deployment (Railway + Supabase)

### Railway
- Single service running the FastAPI app. The Dockerfile builds the frontend (`npm install + npm run build`), copies `frontend/dist` into `backend/static/`, then launches uvicorn.
- FastAPI's `SPAStaticFiles` serves the React bundle at `/` with `index.html` fallback for unknown routes (so React Router's deep links work after refresh). `/api/*` is excluded from the fallback so bad API URLs return real 404s.
- `alembic upgrade head` runs before uvicorn starts (in the entrypoint script). New migrations apply automatically on deploy.
- Auto-deploys on push to `main` IF CI is green.
- Environment variables managed in Railway's Variables tab. Changes trigger a redeploy.
- Free tier covered by the GitHub Student Developer Pack.

### Supabase
- Hosts the production Postgres database (project `uatx-wechat`, region `aws-1-us-west-1`).
- Hosts the production Storage bucket `listing-images`, configured public-read.
- We do NOT use Supabase Auth, Realtime, Edge Functions, or anything else. Just Postgres + Storage.
- Free tier is plenty.

### Domain
- `https://uatxwechat-production.up.railway.app` — Railway's default subdomain. No custom domain configured.

### Stripe (prod webhook setup)
For Stripe in prod, the team had to (one-time):
1. Go to https://dashboard.stripe.com/test/webhooks → Add endpoint.
2. URL: `https://uatxwechat-production.up.railway.app/api/stripe/webhook`.
3. Events: `account.updated` + `checkout.session.completed`.
4. Reveal the signing secret → paste into Railway as `STRIPE_WEBHOOK_SECRET` (different from the local `whsec_`).

The local and prod webhook secrets are different — each endpoint in Stripe has its own.

---

## 23. Conventions

These are documented in CLAUDE.md but worth repeating because they bite.

### Backend
- All API routes under `/api/`. The React app is served at `/`.
- One router file per resource.
- Every user-scoped route uses `Depends(require_user)`. **Never** read identity from a header, query param, or body. **Never** the X-Username trick.
- Pydantic schemas for every request and response. Don't return raw SQLAlchemy models — always use `response_model=`.
- Errors: `HTTPException(status_code, detail)`. Validation 422 is automatic via Pydantic.
- DB access goes through `get_db()` which yields a session and closes it after the request.
- No raw SQL unless necessary. When you do, parameterize.

### Frontend
- TypeScript strict. `any` only with a comment explaining why.
- Every fetch has a visible loading state AND a visible error state.
- `apiRequest` for anonymous calls; `useApi.request` for authenticated calls (it attaches the Clerk JWT).
- Routing via React Router. URLs are bookmarkable. Refreshing keeps you where you are. Back button works.
- Functional components + hooks. No class components.
- Tailwind for styling. Brand color amber-600.
- Controlled form components. Disable submit while in flight.

### Database
- snake_case for tables and columns.
- Real foreign keys with `ON DELETE` chosen explicitly.
- `NOT NULL` is the default.
- Every table has `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`. Mutable tables also have `updated_at`.
- UUIDs for primary keys, EXCEPT `users.id` which is the Clerk user ID string.

### Things NOT to do
- Don't use SQLite (CLAUDE.md hard rule). Use Docker Postgres locally.
- Don't introduce the `X-Username` header pattern.
- Don't denormalize fields that should be foreign keys.
- Don't commit secrets.
- Don't `print()` for debugging in committed code (use `logger`).
- Don't skip loading/error states on a fetch.

---

## 24. Common gotchas

Things that have actually bitten us during development. Pre-emptive defense against repeat damage.

1. **`min-w-0` on flex items.** When `truncate` doesn't seem to work and content overflows on mobile, it's because the flex item's default `min-width: auto` lets it grow to fit content. Add `min-w-0 flex-1` to the parent column. PR #48 fixed an existing horizontal-scroll bug from this.

2. **npm package-lock.json drift across OSes.** macOS and Windows generate slightly different lockfile contents on `npm install`. Each commit cycle threatens a noisy diff. Solution: don't commit lockfile changes from a casual `npm install` — only when adding/removing dependencies.

3. **Integer overflow on `price_cents`.** Postgres INT4 max is ~2.1B. Big-number typos blew through this. Fixed in PR #50 with a Pydantic `le=10_000_000` cap (= $100K). Frontend also clamps on every keystroke.

4. **Stripe Connect same-email rejection.** A seller cannot onboard a Connect account with the same email as the Stripe Dashboard's platform-owner account. Test with a different email.

5. **The `STRIPE_PLATFORM_FEE_BPS` typo bug.** Someone typed letter `o` instead of digit `0` in Railway's variable value. Pydantic refused to parse as int → container crashed at startup → healthcheck timed out → Railway kept serving the OLD container while marking new deploys as failed. Took 30 min to diagnose because the LIVE site looked fine; the next merge was just silently un-deployed. **Always check both: env var values are typed correctly, AND Deployments tab shows green checks.**

6. **The orphaned-commit-after-merge pattern.** Pushing a follow-up commit to a branch AFTER the PR is merged orphans the commit (it's not on `main` but still on the branch). Twice during development the author had to cherry-pick onto a fresh branch. Solution: before every push, check the PR's state via `gh pr view <num> --json state`.

7. **`@clerk.local` placeholder emails.** Clerk's default session token doesn't include the `email` claim. Without it, `auth.py` synthesizes `<sub>@clerk.local` to satisfy the UNIQUE constraint on `users.email`. Looks confusing in Settings and breaks `ADMIN_EMAILS` checks. Fix: configure Clerk's session-token template to include `email`, `name`, `picture` claims. **Manual Clerk dashboard step.**

8. **The `ALLOWED_EMAIL_DOMAINS` default bug** (PR #34). Was previously defaulted to `"student.uaustin.org"` in config.py. When the Clerk JWT started providing real emails, this silently 403'd anyone whose email wasn't `@student.uaustin.org`. Fix: defaulted to empty.

9. **Test DB schema drift after branch switches.** `conftest.py` does `Base.metadata.drop_all` + `create_all` per session, but `metadata` only sees models that are imported. After switching to a branch that doesn't have a model that PREVIOUS branch had created in the test DB, `drop_all` can fail with FK conflicts. **Fix:** `docker exec uatx_wechat_postgres psql -U uatx -d postgres -c "DROP DATABASE IF EXISTS uatx_wechat_test;"` — conftest will recreate it fresh.

10. **Backend tests rely on real Postgres.** Trying to mock the DB is a CLAUDE.md hard rule violation AND a wasted-time trap. Just use the test DB.

11. **Polling collisions with optimistic sends.** The polling loop runs every 4s. Between an optimistic send's POST and its response, the polling cycle might pull the server-side message. The send handler dedupes by ID. Don't break this contract.

12. **Conversation `updated_at` was a no-op bug.** Previously `conv.updated_at = msg.created_at` ran BEFORE the commit, when `msg.created_at` was still None (it's `server_default=func.now()`, computed on INSERT). The conversation's timestamp never moved, so inbox sort by `updated_at` was bunk. Fix: `conv.updated_at = datetime.now(timezone.utc)` explicitly, then commit.

13. **`_upsert_user` was hot.** Pre-PR-#61, every signed-in `/api/listings` hit ran the full upsert (SELECT + maybe UPDATE + commit + refresh). Three DB roundtrips per browse hit. PR #61 trimmed `get_optional_user` to just `db.get(User, sub)` — no upsert, no commit. Faster but the user row must already exist (it does, because /api/me ran on app boot).

14. **CASCADE pitfalls.** `listings → conversations → messages` all CASCADE. Taking down a listing wipes all its conversations + messages. Intended, but worth knowing if you ever build admin moderation tools.

---

## 25. Decisions log

The "why" behind some load-bearing choices.

### Clerk over Supabase Auth
UATX students all have Google accounts. Clerk's Google-sign-in flow was a 10-minute setup. We use Supabase for the DB and Storage but explicitly NOT for Auth — Clerk wins on UX for this user base. We deliberately do NOT restrict to `@student.uaustin.org` because incoming students who don't have school emails yet still need to be able to buy textbooks. (`ALLOWED_EMAIL_DOMAINS` env var is the escape hatch if that policy changes.)

### Docker Postgres for local dev
Keeps local identical to prod Postgres version + features. Without it, we'd find Postgres-only features (ARRAY columns, ILIKE, etc.) break on SQLite. Free, fast, easy.

### `users.id` is the Clerk user ID string, not a UUID
Every JWT carries that ID as `sub`. Setting `users.id = sub` makes JWT-to-DB lookup a single PK SELECT (instead of an indexed-but-not-PK lookup). Worth the slight oddness of having TEXT PKs on one table.

### Per-context chat homes, not a single inbox
Started as `/inbox` for everything. Confusing — you couldn't tell at a glance whether a row was a listing chat or a DM. Reworked across PRs #17–#21: listing chats live in `/my-listings` (seller) or `/my-inquiries` (buyer), DMs live in `/classmates`. Each has its own unread badge in the nav.

### Hard-delete on listing take-down
"Withdrawn" status used to leave zombie rows + orphaned Supabase Storage images. PR #25 changed Take-Down to a real DELETE that cascades to conversations + messages and best-effort deletes the photo. The UI confirms before doing it.

### Stripe Checkout redirect over embedded Elements
Hosted page = zero PCI scope, dramatically less code. Trade-off is one extra redirect, which actually helps trust (Stripe's brand is more credible than ours for handling cards).

### Polling over WebSockets for chat
Existing chat HTTP endpoint is already the source of truth. WebSockets would need parallel transport + connection bookkeeping + sticky sessions. Railway free tier dislikes long-lived connections. Polling composes with the existing 30s `useUnread` poll. 4s cadence is comfortably under the spec's 5s ceiling.

### Per-user rate limit, not per-IP
Dorm networks share NAT. IP-based limiting would punish bystanders when one student misbehaves.

### Frontend feature flags as hardcoded constants
Vite bakes them into the bundle. For toggling without a code change, we'd need env-driven `VITE_*` vars. So far we have one flag (`STRIPE_ENABLED`) and changing it via a one-line PR is fine.

### Wordle backend stores `game_index`, not the word
Backend doesn't know what the words are. Adding new words is a one-line change in `frontend/src/lib/wordle.ts` — no migration. Trade-off: if we reorder the array, history breaks. Treat the array as append-only.

### Admin allowlist by email, not by DB flag
Simple. No migration. Easy to change via Railway env. Two admins is small enough.

---

## 26. PR history (chronological)

Every merged PR through PR #61 (some less-essential intermediate PRs grouped briefly). The PR descriptions on GitHub are the most authoritative source, but here's the running narrative:

| # | One-line summary |
|---|---|
| #1–#3 | Initial scaffolding (Bronze backend + frontend + auth + deploy). |
| #4 | Seed UATX courses + onboarding search (Eitan). |
| #5 | Classmates lookup endpoint + page (Eitan). Silver nontrivial piece. |
| #6 | Deploy to Railway (live URL). |
| #7 | Fix SPA routing fallback for React Router deep links. |
| #8 | Synthesize `<sub>@clerk.local` email for users when Clerk JWT lacks email claim. |
| #9–#16 | Search-first course pickers; enrollment kinds (past/current/upcoming) migration 0005; My classes page polish. |
| #17–#21 | IA restructuring: per-context chat homes. `/my-listings`, `/my-inquiries`, `/classmates` replace single `/inbox`. Sam. |
| #22 | Real-time chat via 4s polling + optimistic message sends. Sam. |
| #23–#24 | Unread badges; per-context unread-counts query. |
| #25 | Hard-delete on listing take-down (replaces soft-withdraw). |
| #26 | Listings.payment_methods column (migration 0007). |
| #27 | Listings categories + Everything Else marketplace (migration 0006). Gold custom feature 2. |
| #28 | Mobile + initial visual pass. Sam. |
| #29 | Classmates: include past + upcoming on the viewer's side (PR by Eitan). |
| #30 | Inbox unread badges + 30s polling foundation. |
| #31 | Fix "Message seller" button on your own listing. |
| #32 | payment_methods preference field on listings (cash/venmo/zelle/paypal/stripe). |
| #33 | Stripe Connect Express checkout. Gold custom feature 3. |
| #34 | Fix `ALLOWED_EMAIL_DOMAINS` default — was silently restricting prod. |
| #35 | Seller profile page (`/users/:userId`). |
| #36 | Cross-cutting authz + input-validation safety tests (10 new). |
| #37 | (closed/abandoned coordination note for Sam — not merged) |
| #38 | Nav cleanup + Sell-a-book form polish (remove "Sell a book" from nav, integer price input, author optional). |
| #39 | Message timestamps under bubbles. |
| #40 | UATX logo + favicon (amber wordmark + wide W). |
| #41 | Match Everything Else price input to the books form (integer-only). |
| #42 | Landing page polish: hero + headline + three feature cards + UATX footer credit. |
| #43 | Classmates lookup expanded to past + upcoming on viewer's side. |
| #44 | Classmates legend label clarified ("Color codes:" → "Their enrollment:"). |
| #45 | Feedback form + "You're enrolled in this class" chip on listings. |
| #46 | Books search + sort + posted-X-ago + custom 404 + hover lift. |
| #47 | "More from this seller" section on listing detail. |
| #48 | Fix horizontal scroll on mobile from non-truncating listing cards. |
| #49 | Spec-compliance pass on README + runway. |
| #50 | Cap listing price at $100K (turn 500 → 422). |
| #51 | README copy edits orphaned from PR #50 (cherry-picked). |
| #52 | Rate-limit message sends (30/min per user). |
| #53 | Make payment-method behavior obvious to listers + buyers (in-app vs arrange-directly chips). |
| #54 | Security: upgrade deps to fix 10 of 12 CVEs (python-jose, python-multipart, starlette, react-router). |
| #55 | UATX Wordle (20 themed words, per-user completion tracking). |
| #56 | Fix seller-profile 401 (was using anonymous fetcher) + show seller on browse cards. |
| #57 | Gray out Stripe UI for UATX-wide launch (STRIPE_ENABLED flag). |
| #58 | Tighten landing-page copy. |
| #59 | Admin-only feedback inbox page (`/admin/feedback`). |
| #60 | Promote "Got an idea?" to an orange button + replace /match tab with "My courses" filter on Books. |
| #61 | Perf: lighter get_optional_user + dual create buttons on My Listings. |

For full details on any PR, run `gh pr view <number> --json title,body,files`.

---

## 27. Known issues & quirks

### Orphaned storage objects
When a listing is hard-deleted, we best-effort delete its Supabase Storage photo via `delete_stored_image()`. Failures are silent. Over time the bucket may accumulate orphaned objects. Not a correctness issue. A future cleanup job could sweep paths that don't have a corresponding `listings.image_url` entry.

### `/match` route still mounted but not linked
PR #60 removed the nav link to `/match` and added a "My courses" filter on `/listings` instead. The `/match` route + `Match.tsx` component are still in the codebase as back-compat for old bookmarks. The matching algorithm is still our spec-required bronze nontrivial logic. If we ever rename or kill the matching feature, update the README and CLAUDE.md to point at where the logic lives now.

### Rate-limit state resets on container restart
In-memory only. Acceptable — the limit is for UX (block button-mashing) not security. A determined bot could restart-cycle the container to evade, but Railway doesn't give end users a way to do that.

### Wordle word reordering breaks history
Word list is just a frontend array. Reordering changes the meaning of `game_index` in stored completions. Append-only is the safe pattern. If you ever need to remove a word, NEVER reorder — leave a placeholder.

### Stripe webhook delivery race
If `account.updated` arrives before the user clicks back into the app, the green "Connected" pill appears on next page load. If multiple webhooks arrive in quick succession (e.g., during onboarding completion), our idempotent handlers cope but the order isn't deterministic. Stripe's documented retry behavior is exponential backoff; our code is tolerant.

### Two starlette CVEs unfixable
Per the security audit (PR #54), we patched 10 of 12 CVEs. Two remaining starlette CVEs (CVE-2025-62727, PYSEC-2026-161) are only patched in starlette 0.49.1+ / 1.0.1+. FastAPI 0.119.x (the latest published) caps starlette < 0.49. We'll pick them up when a newer FastAPI ships. Both unfixable CVEs are in code paths the standard FastAPI request flow doesn't reach.

### Feedback bucket has no admin notification
We added the admin page (PR #59), but submissions don't send email. The admin has to remember to check the page or hit Supabase directly. Email integration via Resend was discussed but punted.

### "Got an idea?" CTA appears on the home page hero
Not exactly an issue, but it's prominent. Worth knowing it's intentional: we want feedback during the rollout.

---

## 28. Future work — features discussed but not built

These came up in conversation during development and were explicitly punted. Each is a real product idea, sketched here for whoever picks them up next.

### Offers / counter-offers
Structured price negotiation. Buyer makes an offer with a price; seller accepts / rejects / counters; buyer can counter the counter. State machine: pending → accepted / rejected / countered. Stored in a new `offers` table with parent_offer_id linking the chain. Embedded as cards in the chat thread so both parties see history. Real estimate: ~3–5 hours of careful work (schema + endpoints + UI cards + state transitions). Designed but not built.

### Email notifications (Resend)
Send emails on key events: new feedback submission (notify admins), checkout completion (notify seller), new message in a long-quiet thread. Easiest path: Resend.com (~5 min signup, free tier 100/day, simple Python SDK). Single new module `app/email.py` with one function. Punted because requires a Resend signup the team hadn't done.

### Per-class study group chats
Group chat with N members instead of 2. Requires a new schema model — current `conversations` is hardcoded 2-party (`buyer_id` + `other_user_id`). Either parallel tables (`group_chats`, `group_chat_members`, `group_messages`) or a unified rewrite. Estimated 3–5 hours; was explicitly discussed but punted before the demo.

### Ride pooling
Match students who need to leave for the same morning class. Time-based + course-based matching. New table + new routes + new UI. Real product fit (UATX has commuter students). Punted as scope-too-big.

### Daily Wordle rotation
Right now the 20 games are static. A "daily" Wordle would rotate one word per day so everyone plays the same word on the same day. Requires: server-side selection function (deterministic on UTC date), per-user-per-day completion records (currently we just have per-user-per-game). The user explicitly said "we don't have to make it so that it updates every day, but we can just have a menu" — so the explicit menu is the chosen MVP.

### Playwright e2e tests
The spec mentioned this as the silver/gold stretch. We chose "more tests" instead (173 pytest > 8–10 minimum). E2e would still be valuable: one Playwright spec covering sign-up → post listing → message seller would prove the full happy path from a real browser.

### Seller profile reviews / ratings
Not discussed but obvious. Buyers rate sellers after a transaction. Requires a new `seller_reviews` table and a moderation policy.

### Wantlists / saved searches
Buyer says "I want PHIL 101 book under $30, alert me." Spec hint #4 in the bookcircle examples. Requires new table + a periodic job + email notifications.

### Visual design pass with a more deliberate aesthetic
The current design is "looks like someone made choices" but not "has a point of view." A real designer could tighten the type scale, color palette beyond amber-600 + slate, spacing system.

---

## 29. Working with this codebase as Claude

Patterns that worked well + things to watch for.

### What worked
- **Trust CLAUDE.md.** It's the source of truth for conventions. If your edit contradicts CLAUDE.md, push back on yourself before pushing back on the user.
- **Read SCHEMA.md** before writing migrations.
- **Use `gh pr view <num>` before pushing follow-up commits.** Avoid the orphan-after-merge trap.
- **Run tests after every nontrivial backend change.** `cd backend && source .venv/bin/activate && pytest -q` takes ~5s.
- **Run `npx tsc --noEmit` after every nontrivial frontend change.** Catches imports / typos / wrong prop shapes instantly.
- **One PR per feature, branched off the latest main.** Avoid stacking PRs unless they truly depend on each other.
- **Commit messages with a short title + multi-paragraph body** explaining the WHY and any tradeoffs. The README pulls from these.
- **Eitan's preference: fix grammar typos by default, mention you did it, don't ask first.** (Established explicitly during PR #61.)

### Where to push back
- Suggested shortcuts that mock the DB → reject (use real Postgres).
- X-Username header pattern → reject (use Clerk JWT).
- SQLite for local dev → reject (use Docker Postgres).
- Denormalizing FK relationships → push back hard.
- Suggestions to skip loading/error states "for now" → no, every fetch needs both.

### Where the agent has gotten things wrong before
- **Used `apiRequest` (anonymous) when an endpoint needed auth.** Caught in PR #56 — the seller profile was 401'ing because `UserProfile.tsx` used the wrong helper.
- **Forgot to add new migrations to the test TRUNCATE list in conftest.py.** Caused test pollution between test files.
- **Reused `_upsert_user` in `get_optional_user` for "consistency" — created a perf regression.** PR #61 fixed.
- **Pushed follow-up commits to merged branches.** Orphaned the work. Cherry-pick recovery.
- **Made up imports / APIs that didn't exist.** CI catches these, but waste a cycle.

### Conventions the agent should always follow in this repo
- Default to writing no comments. Only add when the WHY is non-obvious or there's a real gotcha. Don't describe what the code does — the names already do that.
- Prefer editing existing files over creating new ones.
- Use Bash with care: never run destructive ops (rm -rf, force-push, branch -D) without explicit user confirmation.
- Don't auto-commit. Wait for the user to ask "commit" / "push" / "PR" / "add to pr".
- Don't add features the user didn't ask for.
- When the user describes a UI tweak, ask them to confirm if interpretation is ambiguous, but pick a safe default if they're brief.

### Useful commands to know
```bash
# Backend tests
cd backend && source .venv/bin/activate && pytest -q
cd backend && source .venv/bin/activate && pytest tests/test_listings.py -v -k "my_courses"

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend tests
cd frontend && npx vitest run

# Reset test DB after schema drift
docker exec uatx_wechat_postgres psql -U uatx -d postgres -c "DROP DATABASE IF EXISTS uatx_wechat_test;"

# Check PR state before pushing
gh pr view <num> --json state

# Local Stripe webhooks
stripe listen --forward-to localhost:8000/api/stripe/webhook

# Check who's signed up locally
docker exec uatx_wechat_postgres psql -U uatx -d uatx_wechat -c "SELECT id, email, display_name FROM users ORDER BY created_at DESC LIMIT 10;"

# pip audit
cd backend && source .venv/bin/activate && pip-audit -r requirements.txt

# npm audit
cd frontend && npm audit --omit=dev
```

---

## 30. Quick-start cheatsheet

If you're a future-Claude with zero context and Eitan has just said "let's continue building UATX_WeChat":

1. **Read [CLAUDE.md](CLAUDE.md) first.** It's short. Especially the Runway section.
2. **Read [SCHEMA.md](SCHEMA.md) if you'll touch the DB.**
3. **Skim this file (HANDOFF.md)** for anything that's surprising or relevant to the current task.
4. **`gh pr list`** to see what's open.
5. **`git log --oneline -20`** to see recent work.
6. **Check Docker is up:** `docker ps --filter "name=postgres"` — should show `uatx_wechat_postgres Up X days (healthy)`. If not: `docker compose up -d`.
7. **Start uvicorn:** `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`.
8. **Start Vite:** `cd frontend && npm run dev`.
9. **Visit http://localhost:5173.** Sign in. Confirm `/api/health` returns OK at http://localhost:8000/api/health.

Then ask Eitan what he wants to build. Default to:
- Reading + understanding before suggesting.
- One PR per feature.
- Test before pushing.
- Don't push to a merged branch (check `gh pr view`).
- Eitan likes terse but complete responses with PR URLs.
- He merges his own PRs; don't try to merge for him.
- Sam is on Windows; don't add macOS-only shell snippets to docs without a Windows fallback.

You'll be fine. Good luck.

---

*Written by Claude Opus 4.7 on the last day of the school's subscription — a brain-dump of everything the prior session built, for the next session to pick up cleanly.*
