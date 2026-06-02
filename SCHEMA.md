# Data model

All tables live in a single Postgres database. Snake_case throughout. Every table has `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`; mutable tables also have `updated_at`.

The SQLAlchemy models in `backend/app/models/` are the source of truth at the code level. This doc is the source of truth at the design level — if they disagree, fix one of them.

## Tables

### `users`
- `id` — TEXT, PK. The Clerk user ID (e.g. `user_2abc...`). **Not** a generated UUID — we adopt Clerk's ID so JWT-sub → DB lookup is a primary-key fetch.
- `email` — TEXT, NOT NULL, UNIQUE, length ≤ 255.
- `display_name` — TEXT, NOT NULL, length ≤ 80.
- `avatar_url` — TEXT, nullable. Pulled from Clerk on first sync.
- `created_at`, `updated_at`.

### `courses`
- `id` — UUID, PK.
- `code` — TEXT, NOT NULL, UNIQUE, length ≤ 20. E.g. `PHIL 101`, `MATH 201`.
- `title` — TEXT, NOT NULL, length ≤ 200.
- `created_at`.

### `enrollments`
- `id` — UUID, PK.
- `user_id` — TEXT, FK → `users(id)` ON DELETE CASCADE.
- `course_id` — UUID, FK → `courses(id)` ON DELETE RESTRICT.
- `term` — TEXT, NOT NULL, length ≤ 20. E.g. `Fall 2024`, `Spring 2026`.
- `kind` — TEXT, NOT NULL, one of `past`, `current`, `upcoming`. CHECK constraint enforces. Replaces the boolean `is_current` (migration 0005) so the marketplace can distinguish "I have this book to sell" (past) from "I need this book" (upcoming).
- `created_at`.
- **UNIQUE** (`user_id`, `course_id`, `term`) — you can't be enrolled twice in the same course in the same term.

Why `term` is a string rather than (year, season): readable in psql, fewer joins, terms aren't math.

### `listings`
- `id` — UUID, PK.
- `seller_id` — TEXT, FK → `users(id)` ON DELETE CASCADE.
- `course_id` — UUID, FK → `courses(id)` ON DELETE RESTRICT. Nullable. Books set it (so the matching algorithm can find them); general items leave it NULL.
- `category` — TEXT, NOT NULL. CHECK enforces one of: `book`, `furniture`, `electronics`, `clothing`, `kitchen`, `decor`, `sports`, `transportation`, `other`. Splits the marketplace: books (`category='book'`) live in the textbook experience and surface in matching; everything else lives under `/everything-else`.
- `title` — TEXT, NOT NULL, length ≤ 200. Book title for books, item name for general items. (Renamed from `book_title` in migration 0006.)
- `author` — TEXT, nullable, length ≤ 200. Required for books; NULL for general items. (Renamed from `book_author`.)
- `edition` — TEXT, nullable, length ≤ 40. (Renamed from `book_edition`.)
- `condition` — TEXT, NOT NULL, one of `new`, `like_new`, `good`, `fair`, `poor`. CHECK constraint enforces.
- `price_cents` — INTEGER, NOT NULL, ≥ 0.
- `description` — TEXT, NOT NULL, length ≤ 2000.
- `status` — TEXT, NOT NULL, one of `active`, `reserved`, `sold`, `withdrawn`. Default `active`. CHECK enforces.
- `image_url` — TEXT, nullable, length ≤ 500. Public URL of the listing's photo in Supabase Storage (bucket `listing-images`). Required at create-time for non-book listings (frontend enforces; the Everything Else browse hides rows without an image).
- `created_at`, `updated_at`.

Indexes: `(course_id, status)` for the matching query, `(seller_id, created_at DESC)` for "my listings," `(category, status)` for the Everything Else browse.

### `conversations`
- `id` — UUID, PK.
- `listing_id` — UUID, FK → `listings(id)` ON DELETE CASCADE. **Nullable** — null indicates a direct-message conversation between two students that isn't tied to any listing (started from the Classmates page).
- `buyer_id` — TEXT, FK → `users(id)` ON DELETE CASCADE. For listing convos this is the buyer (seller is implicit from the listing). For DMs this is just "one of the two parties" — the application canonicalizes so that `buyer_id < other_user_id` for DMs, which lets a partial unique index prevent A→B and B→A from creating two rows.
- `other_user_id` — TEXT, FK → `users(id)` ON DELETE CASCADE. The other party. For listing convos this equals `listings.seller_id` (denormalized so membership checks don't have to JOIN). For DMs this is the second user in the pair.
- `created_at`, `updated_at`. `updated_at` bumps whenever a new message lands so inbox sorting is cheap.
- **Partial UNIQUE indexes** instead of a constraint, because the uniqueness rule differs by kind:
  - `uq_conversation_listing` on `(listing_id, buyer_id)` `WHERE listing_id IS NOT NULL` — one thread per (listing, buyer).
  - `uq_conversation_dm` on `(buyer_id, other_user_id)` `WHERE listing_id IS NULL` — one DM per ordered pair (canonicalized).
- **CHECK** (`buyer_id <> other_user_id`) is enforced at the application layer (can't DM yourself, can't message yourself about your own listing).

### `messages`
- `id` — UUID, PK.
- `conversation_id` — UUID, FK → `conversations(id)` ON DELETE CASCADE.
- `sender_id` — TEXT, FK → `users(id)` ON DELETE CASCADE.
- `body` — TEXT, NOT NULL, length ≤ 2000.
- `read_at` — TIMESTAMPTZ, nullable. Set when the *other* party first sees the message.
- `created_at`.

Index: `(conversation_id, created_at)` for fast thread loading.

## Relationships diagram

```
users 1 ─── n enrollments n ─── 1 courses
users 1 ─── n listings    n ─── 1 courses (nullable)
users 1 ─── n conversations (as buyer)
listings 1 ─── n conversations
conversations 1 ─── n messages
users 1 ─── n messages (as sender)
```

## Things deliberately NOT in the schema yet

- **Photos on listings.** Adding when we wire up Supabase Storage in silver/gold.
- **Ratings / reputation.** Likely a gold custom feature.
- **Saved searches.** Likely a gold custom feature.
- **Soft-delete.** We hard-delete via CASCADE. If a teammate needs an audit trail later, switch to a `deleted_at` column then.
