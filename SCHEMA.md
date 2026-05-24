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
- `is_current` — BOOLEAN, NOT NULL. True iff this is a course the user is currently enrolled in.
- `created_at`.
- **UNIQUE** (`user_id`, `course_id`, `term`) — you can't be enrolled twice in the same course in the same term.

Why `term` is a string rather than (year, season): readable in psql, fewer joins, terms aren't math.

### `listings`
- `id` — UUID, PK.
- `seller_id` — TEXT, FK → `users(id)` ON DELETE CASCADE.
- `course_id` — UUID, FK → `courses(id)` ON DELETE RESTRICT. Nullable — a listing might be a general book not tied to a UATX course, though in practice the matching feature only uses listings with a course.
- `book_title` — TEXT, NOT NULL, length ≤ 200.
- `book_author` — TEXT, NOT NULL, length ≤ 200.
- `book_edition` — TEXT, nullable, length ≤ 40.
- `condition` — TEXT, NOT NULL, one of `new`, `like_new`, `good`, `fair`, `poor`. CHECK constraint enforces.
- `price_cents` — INTEGER, NOT NULL, ≥ 0.
- `description` — TEXT, NOT NULL, length ≤ 2000.
- `status` — TEXT, NOT NULL, one of `active`, `reserved`, `sold`, `withdrawn`. Default `active`. CHECK enforces.
- `created_at`, `updated_at`.

Indexes: `(course_id, status)` for the matching query, `(seller_id, created_at DESC)` for "my listings."

### `conversations`
- `id` — UUID, PK.
- `listing_id` — UUID, FK → `listings(id)` ON DELETE CASCADE.
- `buyer_id` — TEXT, FK → `users(id)` ON DELETE CASCADE. The seller side is implicit from the listing.
- `created_at`, `updated_at`. `updated_at` bumps whenever a new message lands so inbox sorting is cheap.
- **UNIQUE** (`listing_id`, `buyer_id`) — one thread per (listing, buyer). The seller is the listing's seller.
- **CHECK** (`buyer_id <> listings.seller_id`) — can't message yourself about your own listing. Enforced at the application layer because cross-row CHECK constraints are awkward in Postgres.

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
