# EITAN.md — onboarding for Eitan

Hey Eitan, welcome to **UATX_WeChat**. This doc gets you from "nothing" to "shipping code" in about 15 minutes. If anything in here is wrong or outdated, fix it as you go — keeping this current is part of working on the project.

## What this is

A textbook marketplace for UATX students. The defining feature is course-history-based matching: when a freshman needs the book for PHIL 101, the app surfaces listings from upperclassmen who took PHIL 101 in past semesters.

- Live URL: **https://uatxwechat-production.up.railway.app**
- Pitch + tier targets: [README.md](README.md)
- Conventions + what's next: [CLAUDE.md](CLAUDE.md) — especially the **Runway** section at the bottom, which is the source of truth for "what do I work on?"
- Data model: [SCHEMA.md](SCHEMA.md)

## How we work

We mostly drive via Claude (Anthropic's CLI agent), sequentially — one teammate at a time. The flow:

1. Pull `main`.
2. Open the Runway in CLAUDE.md.
3. Find the next undone item (`[ ]`).
4. Do it. Tick it (`[x]`). Commit on a feature branch.
5. PR to `main`. CI runs. When it goes green, Sam (or you, once we trust each other on the codebase) merges.
6. Railway auto-deploys on merge.

Commits from every teammate are required by the assignment spec — so when you pick up the next item, do real, attributable work on your account.

## Step 1: Get access

Ask Sam to:

- Add you as a **Collaborator** on https://github.com/Sam-Indyk/UATX_WeChat (so you can push branches and open PRs — `main` is protected, no direct pushes).
- (Optional) Invite you to the **Railway** project and the **Supabase** project. You don't need either for local development, but they're useful if you want to look at production logs or run a SQL query against the cloud DB.

## Step 2: Install prerequisites

- **Python 3.12** — pinned for CI; 3.14 also works in practice.
- **Node 20** or newer.
- **Docker Desktop** — for the local Postgres container.
- **Git**, and ideally the **GitHub CLI** (`gh`) for opening PRs from the terminal.

## Step 3: Clone and run it locally

```bash
git clone https://github.com/Sam-Indyk/UATX_WeChat.git
cd UATX_WeChat
docker compose up -d        # boots Postgres 16 on localhost:5432
```

### Backend

```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# mac/linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Windows:
copy .env.example .env
# mac/linux:
# cp .env.example .env
```

Open `backend/.env` in your editor and **replace the Clerk lines** with these (they're public — not secrets):

```
CLERK_JWKS_URL=https://related-sunbird-55.clerk.accounts.dev/.well-known/jwks.json
CLERK_ISSUER=https://related-sunbird-55.clerk.accounts.dev
CLERK_AUDIENCE=
ALLOWED_EMAIL_DOMAINS=
```

> **"But aren't those secret-looking?"** Clerk's JWKS URL is a *public* key endpoint by design — anyone can fetch it. The actual Clerk *secret* key (the one that would matter) doesn't exist in this codebase because we never need server-to-Clerk calls; we only verify JWTs, which is a public-key operation.

Then:

```bash
alembic upgrade head        # creates the schema in your local Postgres
uvicorn app.main:app --reload
```

You should see the API on http://localhost:8000, with Swagger UI at http://localhost:8000/docs.

### Frontend

In a **separate terminal**:

```bash
cd frontend
npm install

# Windows:
copy .env.example .env
# mac/linux:
# cp .env.example .env
```

Open `frontend/.env` and replace with:

```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_cmVsYXRlZC1zdW5iaXJkLTU1LmNsZXJrLmFjY291bnRzLmRldiQ
VITE_API_URL=http://localhost:8000
```

(The publishable key is literally meant to be public — every Clerk-using site ships it in their bundle.)

Then:

```bash
npm run dev
```

Visit http://localhost:5173 and sign in with any Google account.

## Step 4: Run the tests

```bash
# Backend
cd backend
pytest                      # ~15 tests, all should pass

# Frontend
cd frontend
npm run test                # 2 tests
```

If anything fails on a clean checkout, that's a real bug. Mention it to Sam.

## Step 5: Pick a task

Open [CLAUDE.md](CLAUDE.md), scroll to **Runway**, find the first `[ ]` item. As of the time this doc was written, the top of the to-do list is:

- Seed UATX courses (the `courses` table is empty; the onboarding page has nothing to show)
- Polished onboarding flow
- Listings: browse + create
- Messaging UI
- Matching feed

Pick one. If two of you are about to pick the same thing, talk first.

## Step 6: Commit + PR

```bash
git checkout main && git pull
git checkout -b feat/your-thing          # or fix/your-thing

# do work, then:
git add <specific files>                 # NOT `git add -A` — risks committing .env
git commit -m "Short, clear message"
git push -u origin feat/your-thing
gh pr create                             # or use the GitHub web UI
```

CI runs automatically. **Both jobs (backend pytest + frontend vitest) must go green before merge.** Sam reviews and merges.

## Step 7: What happens after merge

1. GitHub Actions re-runs CI on the merged `main`.
2. Railway detects the new `main`, rebuilds the Dockerfile, redeploys.
3. The container's entrypoint runs `alembic upgrade head` against the Supabase DB, then starts uvicorn.
4. Within ~3 minutes the change is live at https://uatxwechat-production.up.railway.app.

If a deploy goes sideways, Railway's **Deployments → [latest] → Application Logs** tab is where to look.

## Conventions you should internalize

Skim [CLAUDE.md](CLAUDE.md) for the full set. The ones that matter most:

- **Every fetch needs a visible loading state AND a visible error state.** "I'll add it later" means "I'll forget."
- **Real foreign keys, not denormalized name columns.** Join to `users` for a seller name — don't add `seller_name` to `listings`.
- **No SQLite in dev** — use the Docker Postgres so dev and prod match.
- **User identity is the verified Clerk JWT, full stop.** No `X-Username` headers, no usernames in query strings.
- **Don't commit `.env`.** It's gitignored — but verify with `git status` before pushing.
- **Don't `print()` for debugging in committed code.** Remove it or use `logging` before the PR.

## When stuck

1. Search the codebase before asking — most patterns already have a precedent in `routers/`, `pages/`, or `tests/`.
2. The runway in CLAUDE.md tracks decisions. If a step's intent is ambiguous, check its acceptance criteria.
3. Sam: sindyk@student.uaustin.org. He'll get back to you fast.

Welcome aboard.
