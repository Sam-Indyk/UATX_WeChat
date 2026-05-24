# UATX_WeChat

A marketplace and chat app for UATX students to buy and sell used textbooks from each other. The defining feature is course-history-based matching: when you need the book for PHIL 101, the app surfaces listings from upperclassmen who took PHIL 101.

- **Live URL:** TBD (not yet deployed)
- **GitHub:** https://github.com/Sam-Indyk/UATX_WeChat
- **Tier targeted:** Gold
- **Status:** Phase 0 (foundation scaffolded). See [CLAUDE.md](CLAUDE.md) → Runway for the next steps.

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
| Auth | Clerk (Google sign-in, restricted to `@student.uaustin.org`) |
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
| Sam Indyk | sindyk@student.uaustin.org | Repo owner, currently driving Phase 0 |
| _teammate 2_ | _TBD_ | _TBD_ |
| _teammate 3 (optional)_ | _TBD_ | _TBD_ |

Commits from every teammate are required by the spec — coordinate so `git log` reflects real participation.

## Nontrivial logic

- **Bronze:** Course-matching algorithm at [backend/app/routers/matching.py](backend/app/routers/matching.py) → `match_listings_for_user`. Ranks active listings against the signed-in user's current courses, weighted by seller course recency with listing-freshness and price tiebreakers.
- **Silver:** TBD — pick from CLAUDE.md candidates.
- **Gold custom features:** TBD (need 2).

## Design decisions (initial)

- **Clerk over Supabase Auth** — UATX students all have Google accounts on `@student.uaustin.org`; Clerk's Google-sign-in + email-domain restriction made this a 10-minute setup. Supabase still hosts our Postgres.
- **Docker Postgres locally** — keeps local dev identical to prod (same Postgres version, same SQL features) without paying for a cloud dev DB.
- **`users.id` is the Clerk user ID, not a generated UUID** — every JWT carries that ID as `sub`, so verification → DB lookup is a single primary-key fetch.

## Where coding agents helped, where we pushed back

(To be filled in over the project — see README question 6 in the spec.)
