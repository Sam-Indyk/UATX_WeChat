# UATX_WeChat

A marketplace and chat app for UATX students to buy and sell used textbooks from each other. The defining feature is course-history-based matching: when you need the book for PHIL 101, the app surfaces listings from upperclassmen who took PHIL 101.

- **Live URL:** https://uatxwechat-production.up.railway.app
- **GitHub:** https://github.com/Sam-Indyk/UATX_WeChat
- **Tier targeted:** Gold
- **Status:** Bronze + Silver shipped. Gold mostly there — both custom features (image uploads, general marketplace) and the pick-one (real-time chat via polling) are live; mobile pass + visual design pass are the remaining gold-tier work. See [CLAUDE.md](CLAUDE.md) → Runway for the live to-do.
- **Onboarding a teammate?** Have them read [EITAN.md](EITAN.md).

## How to read this repo

1. **[CLAUDE.md](CLAUDE.md)** is the source of truth for conventions, the stack, the nontrivial pieces, and the **Runway** — a sequenced list of every step from "scaffold" to "demo." We work sequentially: read the runway, pick the next undone item, finish it, tick it off, commit.
2. **[SCHEMA.md](SCHEMA.md)** describes the data model.
3. The code lives in `backend/` and `frontend/`.

## Stack at a glance

| Layer | Choice |
|---|---|
| Backend | FastAPI + SQLAlchemy + Alembic |
| Frontend | React + TypeScript + Vite + Tailwind + React Router |
| Database | Postgres — local via Docker, production on Supabase |
| Auth | Clerk (Google sign-in, open to all Google accounts) |
| Hosting | Railway (FastAPI serves the React build at `/`, API at `/api/*`) |
| Tests | pytest (backend), Vitest (frontend) |
| CI | GitHub Actions |

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
| Sam Indyk | sindyk@student.uaustin.org | Repo owner. Built Bronze + Silver + Gold-tier backend / IA / chat / marketplace. |
| Eitan | _TBD_ | Mobile pass + visual design pass (see [EITAN.md](EITAN.md)). |
| _teammate 3 (optional)_ | _TBD_ | _TBD_ |

Commits from every teammate are required by the spec — coordinate so `git log` reflects real participation.

## Nontrivial logic

- **Bronze:** Course-matching algorithm at [backend/app/routers/matching.py](backend/app/routers/matching.py) → `match_listings_for_user`. Ranks active book listings against the signed-in user's current and upcoming courses, weighted by seller course recency with listing-freshness and price tiebreakers.
- **Silver:** Classmates lookup at [backend/app/routers/classmates.py](backend/app/routers/classmates.py) → `GET /api/classmates`. Real cross-table aggregation across `users` × `enrollments` (self-join on course overlap), groups results per classmate with the list of shared courses, deduplicates classmates who share multiple courses.
- **Gold custom feature 1:** Image uploads on listings (Supabase Storage). Optional single image per listing.
- **Gold custom feature 2:** General-purpose marketplace ("Everything Else" tab). Sell furniture, electronics, sports gear, clothing, etc. — anything between UATX students. Category filter + search.
- **Gold "pick one": real-time-ish chat via polling.** `<ConversationThread>` (in [frontend/src/components/ConversationThread.tsx](frontend/src/components/ConversationThread.tsx)) polls `GET /api/conversations/:id/messages` every 4 seconds while a thread is open and merges any new message IDs into the list. When user A sends a message, user B's open thread renders it within 5s without a refresh. **Polling vs. push:** the existing chat HTTP endpoint is already the source of truth for messages; SSE/WebSockets would have required a parallel transport, server-side connection bookkeeping, and a sticky-session-friendly host. Railway's free tier doesn't love long-lived connections. Polling composes trivially with our existing `useUnread` polling pattern (which runs at 30s), uses the same auth/JWT path, and gracefully degrades on flaky networks. 4s is well under the spec's 5s ceiling.

## Silver-tier behaviors worth calling out

- **Optimistic message sends.** When you click Send, your message appears in the thread immediately with a dimmed bubble + "Sending…" caption. The POST then swaps the optimistic bubble for the server's confirmed message, or — if the request fails — removes the bubble and restores your typed text so you can fix-and-retry without re-typing. Lives in [`<ConversationThread>`](frontend/src/components/ConversationThread.tsx) and composes with the 4s polling: if a poll picks up the server-side version of your message between the optimistic-add and POST-resolve, the resolve handler dedupes.

## Design decisions (initial)

- **Clerk over Supabase Auth** — UATX students all have Google accounts; Clerk's Google-sign-in flow made this a 10-minute setup. We deliberately do NOT restrict to `@student.uaustin.org` — incoming students who don't have their school email yet need to be able to buy books from upperclassmen. Supabase still hosts our Postgres.
- **Docker Postgres locally** — keeps local dev identical to prod (same Postgres version, same SQL features) without paying for a cloud dev DB.
- **`users.id` is the Clerk user ID, not a generated UUID** — every JWT carries that ID as `sub`, so verification → DB lookup is a single primary-key fetch.

## Where coding agents helped, where we pushed back

- **Helped:** scaffolding (FastAPI + SQLAlchemy + Alembic + Vite + Tailwind), boilerplate routers + Pydantic schemas, the matching ranking query, the per-context unread-count SQL (one query with three SUM(CASE) clauses), and the IA restructuring across PRs #17–#22 (per-context chat homes, optimistic sends, polling). Generally fast at "translate this design into idiomatic code in this stack."
- **Pushed back:** initial passes leaned on suspicious shortcuts — mocking the DB in tests, an `X-Username` header for auth, SQLite for local dev. All explicitly forbidden in CLAUDE.md and reverted on review. Also caught a latent `conversations.updated_at` bug where assigning `msg.created_at` (None pre-commit) was a no-op — fix is to use `datetime.now(timezone.utc)` explicitly. A few times an agent invented imports or APIs that didn't exist; CI caught those.
