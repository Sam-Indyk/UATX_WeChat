# EITAN.md — onboarding & handoff for Eitan

Hey Eitan — Sam here. I just pushed a big chunk and I'm done for the day. **It's your turn.** This doc is the handoff: what changed, what was intentional, what you should work on next. Skim it once and you should know what to touch and what to leave alone.

Pitch + tier targets: [README.md](README.md). Conventions + the full to-do list: [CLAUDE.md](CLAUDE.md). Data model: [SCHEMA.md](SCHEMA.md). Live URL: **https://uatxwechat-production.up.railway.app**.

## What's shipped since you last worked

Substantial chunk. A quick tour:

- **Enrollment kinds**: courses are now tagged `past` / `current` / `upcoming`. The matching algorithm uses current + upcoming for the buyer's relevant courses, past + current for crediting sellers. `/onboarding` was renamed to `/my-classes` (more accurate — you come back every semester).
- **Per-context chat homes**: the old `/inbox` is gone. Conversations live in three semantic places: `/my-listings` (seller view, with a Chat + Settings subtab per listing), `/my-inquiries` (buyer view of listing conversations), and `/classmates` (DMs). Each one has its own unread badge in the nav.
- **Image uploads** on book listings + the general marketplace, via Supabase Storage. The bucket is `listing-images`, public-read. Avatars use the same bucket under `avatars/<user_id>/...`.
- **General marketplace** ("Everything else" tab): non-book listings with categories (furniture, electronics, clothing, kitchen, decor, sports, transportation, other). Photo required at create time. Browse shows thumbnails. Books browse stays text-first.
- **Settings page**: lets you upload an avatar and rename yourself. Hides the `@clerk.local` placeholder email row (a synthesized fallback we use when Clerk's JWT doesn't carry a real email).
- **Real-time-ish chat via polling**: `<ConversationThread>` polls every 4s while open. New messages from the other party appear without a refresh.
- **Optimistic message sends**: the message bubble appears immediately (dimmed, "Sending…") and either gets confirmed by the server or rolls back on failure with the input restored.
- **Per-thread unread pills + per-listing pills + nav badges**: the whole notification picture is in sync now. Open a thread → mark-read fires → badge drops within the same second.
- **"Take down" hard-deletes**: clicking Take Down on a listing actually removes the row (cascades to its conversations + messages) and best-effort deletes the photo from Supabase Storage. Used to set status=withdrawn which left zombies; doesn't anymore.
- **Profile picture upload**, classmates click-to-DM, per-classmate unread, search-first course pickers in NewListing + Listings filter, and a "My classes" nav link plus a persistent "Update my classes →" link in the For-my-courses header.

**115 backend tests, all green. Frontend type-check clean.**

## Decisions to respect (don't accidentally undo these)

These were deliberate calls. If you find yourself "fixing" one, double-check that the fix isn't reverting an intentional choice.

| Decision | Why |
|---|---|
| **No `/inbox` page** | Each chat type has its own home now. The catch-all was confusing — you couldn't tell at a glance what kind of conversation a row was. `/inbox/:id` still works as a back-compat redirect for old links. |
| **Three per-context nav badges** instead of one | Users want to know *which* kind of unread they have. Sourced from one batched `GET /api/me/unread-counts` so it's cheap. |
| **Books browse has no inline thumbnails** | Books are recognizable by title + author + course code. Click into the listing to see the cover. Keeps Books and Everything Else visually distinct. |
| **Everything Else hides image-less listings** | The grid is image-heavy by design; rows without a photo would look broken. Backend filters them out of `GET /api/listings?category=non-book`. |
| **You can't post a non-book from "Sell a book"** | Two separate forms (`/listings/new` and `/everything-else/new`), each with the category fixed. Sam wanted strict separation. |
| **Take down = hard delete** | Withdrawn listings used to accumulate (and their Supabase Storage images). Now Take Down deletes the row and the photo. UI confirms first. |
| **Polling, not WebSockets** | Chat refreshes every 4s; nav badge every 30s. Railway's free tier doesn't love long-lived connections, and HTTP composes with everything else we already have. |
| **Optimistic sends with rollback** | Snappy feel + handles network failure cleanly. Don't disable the send input — multiple optimistic sends in flight is fine. |
| **`@clerk.local` placeholder emails hidden in UI** | We synthesize them when Clerk's JWT has no email claim. Showing them to users confuses them. Configure a Clerk JWT template (see CLAUDE.md → Auth section) to get real emails. |
| **`conversations.updated_at` bumps on each message** | Silver hit a latent bug here — the old code assigned `msg.created_at` which is None pre-commit (no-op). Now uses `datetime.now(timezone.utc)` explicitly. Don't "simplify" it back. |
| **Browser back/forward fully works** | Every page that has internal state (tab, selected conversation, filter) uses URL search params. Refreshing or bookmarking preserves state. |

## Where we are on the tier checklist

```
Bronze   [x] all invariants
Silver   [x] second nontrivial piece (classmates lookup)
         [x] optimistic message sends
         [x] bookmarkable URLs + back button
         [ ] visual design pass               ← YOUR JOB
         [ ] e2e Playwright test
Gold     [ ] mobile pass                       ← YOUR JOB
         [x] pick-one: real-time chat via polling
         [x] custom feature 1: image uploads
         [x] custom feature 2: general marketplace
         [ ] README gold-tier description update
```

We're one big visual/mobile push and one README pass away from full gold.

## Your job — MVP

**Two things, in this order:**

### 1. Mobile pass (gold-tier requirement)

Sam will be opening the live URL on his phone when he tests. Every page needs to work at phone width. Specifically:

- No horizontal scrolling on any page.
- Tap targets ≥ 44px (so a finger can hit them).
- **Two-pane chat layouts** (`/my-listings/:id?tab=chat`, `/my-inquiries`, `/classmates`) need a mobile collapse strategy. Options: hide the list when a thread is open + show a "← back to list" link; or use a slide-over panel. Pick whichever you can ship cleanly.
- The top nav has a lot of links now (6 signed-in: My classes, For my courses, Classmates, My listings, My inquiries, Sell a book). Will overflow on phones. Consider a hamburger menu at narrow widths.
- **Camera capture from the phone**: file inputs already work on mobile, but adding `capture="environment"` to image inputs lets users open the phone camera directly instead of going through the gallery. Big UX win for marketplace photos. Apply to: NewItem.tsx, NewListing.tsx photo field, ListingSettingsForm photo upload, Settings avatar upload.

### 2. Visual design with a point of view (silver requirement, also feeds gold)

Right now the app is unstyled Tailwind defaults — black-on-white, slate borders. Functional but no aesthetic. Sam's preference: **minimalist** — clean type, generous whitespace, restrained color, no decoration for decoration's sake. Don't go heavy.

Concrete suggestions (you choose the actual direction):
- Pick a 2-color accent palette beyond slate. Maybe a single brand color (warm orange? cool blue?) used sparingly for primary actions.
- Type scale: pick three sizes and stick to them. The current code has font sizes scattered between `text-xs`, `text-sm`, `text-base`, `text-lg`, `text-xl`, `text-2xl` — that's too many.
- Consistent spacing rhythm. The cards in My Listings, My Inquiries, Everything Else, Browse all use slightly different paddings.
- Empty states feel a bit grim ("No listings yet."). A bit of warmth without being twee.
- Consider **collapsing pages** to reduce the nav. For instance: My Listings + My Inquiries could be one "Activity" page with two tabs. The point: fewer top-level destinations, cleaner mental model. Sam's open to consolidating if you have a coherent take.

**Don't redesign the data model or the API.** Visual changes only — Tailwind classes, layout primitives, maybe shared component extraction. If you want to add a real component library (Headless UI? Radix?) that's fine, but consider whether the minimalist direction needs one.

## Nice-to-haves if you have extra time

Listed roughly in priority order. None of these block gold; all of them would make the demo more impressive.

1. **Stripe payments.** Buyer agrees to pay → seller okays the payment → buyer confirms receipt → funds release. Three-step state machine fits the conversation state pattern. Stripe Connect for marketplace flows; standalone or test-mode is fine for the demo. Adds real-world weight to the project. Big feature; only start if mobile + visual are solid.
2. **Negotiation in chat.** Inline "offer / counter-offer / accept / decline" actions in the conversation thread. Real state machine, ties into the listing's `status` field (active → reserved → sold). Smaller than Stripe but still a chunky feature.
3. **"Bulletin board"** — after a completed purchase, the buyer and seller take a photo together that gets posted to a public feed. Nice community touch. Smallest of the three.
4. **Take-photo-from-phone** (covered above under the mobile pass — already MVP, not extra).

## Quick setup refresher

If your local checkout is stale (which it probably is — a lot has changed):

```bash
git checkout main
git pull
docker compose up -d                          # if Postgres isn't already running
cd backend
.venv\Scripts\activate                        # or your venv equivalent
pip install -r requirements.txt               # in case new deps
alembic upgrade head                          # apply migrations 0001-0006
pytest -q                                     # 115 tests should pass

cd ../frontend
npm install                                   # in case new deps
npm run dev                                   # http://localhost:5173
```

Frontend `.env`: same Clerk publishable key as before, plus `VITE_API_URL=http://localhost:8000`.

Backend `.env`: same Clerk URLs, same local Postgres URL. The Supabase Storage vars (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) only matter for production image uploads — locally, the upload endpoint returns 503 if those aren't set, but you can develop the UI around it just fine.

## Work flow

Same as before. Branch off main, work on one feature at a time, PR, watch CI, merge. The runway in [CLAUDE.md](CLAUDE.md) is still the source of truth for "what's next" — tick items as you finish them.

**`main` is protected** — push to a branch, open a PR, let CI go green, then merge. PRs from your account give the project the multi-teammate `git log` it needs for the assignment spec.

## Conventions you should still keep in mind

- Loading + error states on every fetch.
- Real foreign keys, no denormalized name columns.
- No SQLite in dev — use Docker Postgres.
- User identity = verified Clerk JWT, never a header or query param.
- Don't commit `.env`.
- No `print()` for debugging in committed code.
- **Don't break the URL bookmarking story.** Refresh + back button working everywhere is a silver-tier deliverable that's already done. Don't introduce client-side-only state for things users would expect to be linkable.

## When stuck

1. Search the codebase first — most patterns have precedent (e.g., file uploads, polling, optimistic updates, subtab routing).
2. CLAUDE.md → Runway has acceptance criteria for most items.
3. The git log is dense but useful — each PR's commit message has a "WHY this design" section.
4. Sam: sindyk@student.uaustin.org.

Have fun. The product is in good shape; you mostly get to make it look good and feel right on a phone.
