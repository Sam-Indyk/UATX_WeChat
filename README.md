# UATX_WeChat

A marketplace and chat app for UATX students to buy and sell used textbooks and other goods from each other. The defining feature is course-history-based matching: when you need the book for SWE, the app surfaces listings from upperclassmen who took SWE (if we actually use textbooks in the future, hehe).

- **Live URL:** https://uatxwechat-production.up.railway.app
- **GitHub:** https://github.com/Sam-Indyk/UATX_WeChat
- **Tier targeted:** Gold
- **Status:** All three tiers shipped. Three gold custom features (image uploads, general-purpose marketplace, Stripe Connect checkout), the gold pick-one (real-time chat via polling), the silver second nontrivial piece (classmates lookup), and the mobile + visual passes are live. 161 backend tests + 2 frontend tests passing in CI; the optional silver e2e Playwright test isn't done — the spec frames it as "OR more tests" and we leaned into "more tests" (started this project at ~9 tests, now at 161). See [CLAUDE.md](CLAUDE.md) → Runway for the full history.
- **Sam communicating changes to Eitan** [EITAN.md](EITAN.md).

## How to read this repo

1. **[CLAUDE.md](CLAUDE.md)** is the source of truth for conventions, the stack, the nontrivial pieces, and the **Runway** (sequenced list of every step from "scaffold" to "demo"). We work sequentially: read the runway, pick the next undone item, finish it, tick it off, commit.
2. **[SCHEMA.md](SCHEMA.md)** describes the data model.
3. The code lives in `backend/` and `frontend/`.

## Stack at a glance

| Layer | Choice |
|---|---|
| Backend | FastAPI + SQLAlchemy + Alembic |
| Frontend | React + TypeScript + Vite + Tailwind + React Router |
| Database | Postgres — local via Docker, production on Supabase |
| Auth | Clerk (Google sign-in, open to all Google accounts) |
| Payments | Stripe Connect Express (test mode); listing photos + avatars in Supabase Storage |
| Hosting | Railway (FastAPI serves the React build at `/`, API at `/api/*`, one URL, no CORS in prod) |
| Tests | pytest (backend, 161 tests), Vitest (frontend) |
| CI | GitHub Actions — runs on every push, gates Railway deploy on green |

## Run it locally

Prereqs: Python 3.12, Node 20+, Docker Desktop.

```bash
# 1. Postgres
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate              # Windows; use source .venv/bin/activate on mac/linux
pip install -r requirements.txt
copy .env.example .env              # then fill in CLERK values
alembic upgrade head
uvicorn app.main:app --reload

# 3. Frontend (separate terminal)
cd frontend
npm install
copy .env.example .env              # then fill in VITE_CLERK_PUBLISHABLE_KEY
npm run dev
```

Visit http://localhost:5173 for the frontend. The API is on http://localhost:8000 with docs at `/docs`.

### Tests

```bash
cd backend
pytest

cd frontend
npm run test
```

## Team

| Person | Email | Focus |
|---|---|---|
| Sam Indyk | sindyk@student.uaustin.org | Repo owner. Built the original backend scaffold + auth + deploy pipeline. Owned the IA restructuring (per-context chat homes across PRs #17–#21), real-time chat polling, optimistic message sends, image uploads via Supabase Storage, the general-purpose "Everything Else" marketplace, and the initial mobile + visual passes (PR #28). 51 commits on `main`. |
| Eitan Zarin | ezarin@student.uaustin.org | Course catalog seed + onboarding search (PR #4), the classmates lookup foundation (PR #5), the classmates expansion to past + upcoming with color-coded chips (PR #29), the Stripe Connect Express checkout integration end-to-end (PR #33, including the local + Railway env-var wiring and the same-email Connect rejection caveat), the seller-profile page (PR #35), the cross-cutting authz safety test pass (PR #36), the landing-page hero + feature highlights (PR #42), the logo + favicon (PR #40), the search / sort / freshness / 404 polish (PR #46), the feedback form (PR #45), the "you're in this class" indicator, the "More from this seller" section, the mobile horizontal-scroll fix (PR #48), and the spec-compliance README pass. 42 commits on `main`. |

Both teammates have real distributed commit history. first few commits were both teammates. PRs #4-#27 is Sam. #28 and further is Eitan. The runway in CLAUDE.md tracks every step.

## Nontrivial logic

- **Bronze:** Course-matching algorithm at [backend/app/routers/matching.py](backend/app/routers/matching.py) → `match_listings_for_user`. Ranks active book listings against the signed-in user's current and upcoming courses, weighted by seller course recency with listing-freshness and price tiebreakers. Note that the website currently allows emails that are not @uaustin.org so that we can test with our other email accounts. This will change in the future when we deploy for all UATX students to use!
- **Silver:** Classmates lookup at [backend/app/routers/classmates.py](backend/app/routers/classmates.py) → `GET /api/classmates`. Real cross-table aggregation across `users` × `enrollments` (self-join on course overlap), groups results per classmate with the list of shared courses, deduplicates classmates who share multiple courses.
- **Gold custom feature 1: Image uploads on listings.** Optional single image per listing via Supabase Storage. Backend enforces a 5 MB cap + JPEG/PNG/WebP MIME type + seller-only auth. Avatars use the same bucket under `avatars/<user_id>/...`. Listing photos are removed on "Take down" via `storage.delete_stored_image` (best-effort). When using mobile, one can open their camera and take a photo of the item they are trying to sell.
- **Gold custom feature 2: General-purpose marketplace ("Everything Else" tab).** Listings stop being book-only. A `category` field on `listings` (`book`/`furniture`/`electronics`/`clothing`/`kitchen`/`decor`/`sports`/`transportation`/`other`) lets users sell anything that makes sense between UATX students. A new `/everything-else` page (image-heavy card grid, category filter, search) browses the non-book listings; the existing books browse stays separate. The course-matching algorithm filters to `category='book'` so non-book items don't muddy the recommendations.
- **Gold custom feature 3: Stripe Connect Express checkout.** Real  marketplace payments via Stripe's Connect Express product (currently still using test mode, so realy payments cannot be sent through until we confirm security and set more parameters for puchases - this includes determining how much of a haircut we are going to give the seller). Sellers onboard a connected account from `/settings`; buyers see "Pay with Stripe" on listings where the seller both has the `stripe` payment method enabled AND has completed Connect onboarding (the latter flag flips via the `account.updated` webhook). Checkout uses Stripe's hosted page (destination charge with optional platform fee), and the listing's status moves to `reserved` when `checkout.session.completed` fires. All Stripe endpoints return 503 when `STRIPE_SECRET_KEY` is empty (so prod fails gracefully if the keys aren't configured). Lives in [backend/app/routers/stripe_routes.py](backend/app/routers/stripe_routes.py).
- **Gold "pick one": real-time-ish chat via polling.** `<ConversationThread>` (in [frontend/src/components/ConversationThread.tsx](frontend/src/components/ConversationThread.tsx)) polls `GET /api/conversations/:id/messages` every 4 seconds while a thread is open and merges any new message IDs into the list. When user A sends a message, user B's open thread renders it within 5s without a refresh. **Polling vs. push:** the existing chat HTTP endpoint is already the source of truth for messages; SSE/WebSockets would have required a parallel transport, server-side connection bookkeeping, and a sticky-session-friendly host. Railway's free tier doesn't love long-lived connections. Polling composes trivially with our existing `useUnread` polling pattern (which runs at 30s), uses the same auth/JWT path, and gracefully degrades on flaky networks. 4s is well under the spec's 5s ceiling.

## Silver-tier behaviors worth calling out

- **Optimistic message sends.** When you click Send, your message appears in the thread immediately with a dimmed bubble + "Sending…" caption. The POST then swaps the optimistic bubble for the server's confirmed message, or — if the request fails — removes the bubble and restores your typed text so you can fix-and-retry without re-typing. Lives in [`<ConversationThread>`](frontend/src/components/ConversationThread.tsx) and composes with the 4s polling: if a poll picks up the server-side version of your message between the optimistic-add and POST-resolve, the resolve handler dedupes.
- **Bookmarkable URLs end to end.** Every page with internal state carries that state in URL search params — `/my-listings?tab=everything-else`, `/listings?q=republic&sort=high`, `/classmates?dm=<uuid>`. Refresh keeps you where you were; back/forward works.
- **Visual design pass.** Landing page has a real hero with logo + headline + value prop + feature cards; brand mark (UATX wordmark over a wide W) in amber-600 lives at the favicon and in the nav. Type scale, color palette, and spacing are consistent across pages. Mobile collapses cleanly: two-pane chat layouts switch to list-or-thread below `md`, the nav becomes a hamburger, no horizontal scroll (defended in depth via `overflow-x-hidden` on body).

## Design decisions

- **Clerk over Supabase Auth** — UATX students all have Google accounts; Clerk's Google-sign-in flow made this a 10-minute setup. We deliberately do NOT restrict to `@student.uaustin.org`. Many incoming students don't have their school email yet, but still need to be able to buy books from upperclassmen. Supabase still hosts our Postgres. (`ALLOWED_EMAIL_DOMAINS` env var stays as the escape hatch if we change our mind.) 
- **Docker Postgres locally** — keeps local dev identical to prod (same Postgres version, same SQL features) without paying for a cloud dev DB.
- **`users.id` is the Clerk user ID, not a generated UUID** — every JWT carries that ID as `sub`, so verification → DB lookup is a single primary-key fetch.
- **Per-context chat homes, not a single inbox** — listing conversations live in `/my-listings` (as seller) or `/my-inquiries` (as buyer); DMs live in `/classmates`. The old single `/inbox` page was confusing — you couldn't tell at a glance what kind of conversation a row was about. Each chat type now has a semantic home, and the nav carries three per-context unread badges sourced from one batched `GET /api/me/unread-counts` query.
- **Hard-delete on listing take-down, not soft-withdraw** — withdrawing a listing used to leave a zombie row + an orphaned Supabase Storage image. "Take down" now hard-deletes the listing (cascades to its conversations + messages via FK ON DELETE CASCADE) and best-effort deletes the photo. UI confirms first.
- **Stripe Checkout redirect over embedded Elements** — Stripe hosts the entire payment UI, so we never touch raw card numbers and our PCI scope is zero. (There is a possibility for embedding the Stripe stuff, but this would simply be fore asthetic purposes and to avoid a redirect. Having the redirect probably makes the website more trustworthy too, as Stripe has a good reputation.) The redirect adds one extra navigation but cuts dramatically more code (no Elements provider, no PaymentIntent client-secret dance, no card-field state machine). Acceptable trade-off for a demo, and advantageous for reputation purposes.

## Where coding agents helped, where we pushed back

- **Helped:** scaffolding (FastAPI + SQLAlchemy + Alembic + Vite + Tailwind), boilerplate routers + Pydantic schemas, the matching ranking query, the per-context unread-count SQL (one query with three SUM(CASE) clauses), the IA restructuring across PRs #17–#22 (per-context chat homes, optimistic sends, polling done by Sam), the mobile collapse strategy for the two-pane chat layouts (PR #28), the Stripe Connect integration including the webhook signature verification (PR #33), the search/sort/freshness/404 polish pass (PR #46), and the spec-compliance audit. Generally fast at "translate this design into idiomatic code in this stack."
- **Pushed back:** initial passes leaned on suspicious shortcuts. This included mocking the DB in tests, which was an easy fix, as we discussed in class. It also included an `X-Username` header for auth, SQLite for local dev. All explicitly forbidden in CLAUDE.md and reverted on review. Caught a latent `conversations.updated_at` bug where assigning `msg.created_at` (None pre-commit) was a no-op — fix is to use `datetime.now(timezone.utc)` explicitly. Caught a worse latent bug while shipping the Clerk JWT template: `ALLOWED_EMAIL_DOMAINS` defaulted to `"student.uaustin.org"` in config.py (so the previously-dormant domain check started rejecting non-UATX accounts in prod the moment Clerk started providing a real email claim) — fixed by flipping the code default to empty in PR #34. During the mobile polish PR the agent's `npm install` regenerated `package-lock.json` with cosmetic drift across npm versions; Eitan reverted that to avoid churn in Sam's environment. Twice the agent pushed a commit to a branch that was already been merged into main, so we made sure to always have Claude check CI and merge status to prevent this weird but usually trivial mistake. This would orphan the work and forcing a cherry-pick onto a fresh branch — fixable but a tax we paid for not always checking PR state before pushing. A few times an agent invented imports or APIs that didn't exist; CI caught those.

**Extra notes after presentation**
Stripe works now. I made an error on Railway, typing the letter o instead of the number 0 into one of the variable holders. 

Rate limiting added after surge of messages from Pierce Crist. 30 messages per 60 second window returning 429 with Retry-After header on violation. Based on user.id instead of IP, because dorm rooms will share NATs, so IP keying would be unfair to the roommates of the perpetrator.
