# Hey Sam — bug-hunt pass before the demo

_Written 2026-06-04 by Eitan (via Claude). Untracked file, just a handoff note._

Eitan asked me to leave you this. He's heads-down on the visual polish pass before the demo, and you're the one with the eye for catching things that slip past automated tests. Could you do a thorough live-URL pass and flag anything that breaks or feels off?

## Recent surface area (since you last reviewed)

- **PR #36** — 10 new authz/validation safety tests. Backend now 155 tests, all passing.
- **PR #35** — Seller profile page at `/users/:userId`, reachable from any listing's seller name. "Message me" CTA; self-view replaces it with "Manage your listings".
- **PR #34** — Fix for `ALLOWED_EMAIL_DOMAINS` defaulting to `"student.uaustin.org"` in `config.py`. Non-UATX accounts were silently 403'd in prod once the Clerk JWT template started providing real emails. Local was fine because `.env` overrode the default.
- **PR #33** — Stripe Connect Express checkout. Sellers onboard via `/settings`, buyers see "Pay with Stripe" on enabled listings, redirect to Stripe-hosted page, webhook flips listing → `reserved`. Eitan verified locally with the test card + the onboarding half on prod.
- **PR #32** — Payment methods preference (cash / venmo / zelle / paypal / stripe) on listings; surfaces as an "Accepts:" line on the detail page.

Tests passing: 155 backend, 2 frontend, tsc clean. CI green on `main`.

## High-leverage things to test

Open https://uatxwechat-production.up.railway.app with two browser profiles (or one normal + one incognito) so you can act as both seller and buyer.

### 1. Stripe payment flow end-to-end

- Connect a seller account via `/settings`. **Use a different Google email than your Stripe Dashboard owner** — same-email Connect is rejected by Stripe (not our bug, but it'll waste 10 minutes if you hit it).
- Post a listing with Stripe checked in payment methods.
- From a buyer account, hit "Pay with Stripe" → use card `4242 4242 4242 4242`, any future expiry, any CVC, any ZIP.
- Confirm listing flips to `reserved` and the `?stripe=success` banner shows.
- Try the cancel flow too (`?stripe=cancel`).
- https://dashboard.stripe.com/test/payments should show the test charge.

### 2. Seller profile page (`/users/:userId`)

- Click a seller's name on any listing → profile renders with their active listings?
- Self-view (click your own name on your own listing) → "Manage your listings" link instead of "Message me"?
- Direct URL `/users/user_garbage` → graceful 404, not blank/500?
- "Message me" → creates a DM or reopens existing; idempotent both directions?

### 3. Real-time chat polling + optimistic sends

- Two browsers, two users, same conversation open.
- A types → B sees it within ~5 seconds without refresh?
- DevTools → Network → Offline → type and send → does it surface a real error, or silently swallow?
- Send a message and immediately scroll up to read history — does the new-message arrival jump you back to bottom unexpectedly?

### 4. Cross-user authz (UI-hidden cases the backend must enforce)

- Self-message-on-own-listing → UI hides, backend should 400.
- Self-DM (`POST /api/users/<my-own-id>/dm`) → backend should 400.
- URL-typing into another user's listing-management / conversation / settings → 403 / 404 / no data leak.

### 5. State preservation + back button

- `/my-listings?tab=everything-else` refresh → tab persists?
- Browser back button after deep navigation (listing → seller profile → another listing) → step-by-step?
- Sign out from a protected route → redirects cleanly to `/sign-in`?

### 6. Empty / loading / error states

- Brand-new account → does every page render a sensible empty state instead of stuck "Loading…" or blank?
- Slow network (DevTools throttling: Slow 4G) → visible loading indicators everywhere?
- Garbage IDs in URL (`/listings/abc-def`) → graceful error vs raw 500 / blank screen?

### 7. Mobile width

- DevTools → toggle device → iPhone 14 (or any narrow viewport).
- No horizontal scroll on any page.
- Hamburger menu reliable; doesn't get stuck open after navigation.
- Two-pane chat layouts (My Listings, My Inquiries, Classmates) collapse cleanly to list-OR-thread below `md` width.

## Where to record findings

Whatever's easiest — GitHub issues, a markdown file in the repo, or paste into a Slack DM with Eitan. He'll triage by demo impact and either fix on the spot or punt.

Thanks man.
