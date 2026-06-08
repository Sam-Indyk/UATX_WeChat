import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { useApi } from "../lib/api";
import { formatRelativeDate } from "../lib/date";
import type { Conversation, PublicUser } from "../lib/types";
import { NON_BOOK_CATEGORIES } from "../lib/types";

/** Public seller profile reachable from any listing's seller-name link.
 *  Shows the seller's avatar/name plus their active listings, with a
 *  "Message me" button that creates (or reopens) a DM. The same page
 *  also handles the self-view — viewing your own profile hides the
 *  Message-me button and surfaces a Manage link instead. */
export default function UserProfile() {
  const { userId } = useParams();
  const { user: clerkUser } = useUser();
  const { request } = useApi();
  const nav = useNavigate();

  const [profile, setProfile] = useState<PublicUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!userId) return;
    // Auth'd request (attaches the Clerk JWT) — the endpoint requires
    // sign-in. Previously this used apiRequest (anonymous) which 401'd
    // every time.
    request<PublicUser>(`/api/users/${userId}`)
      .then(setProfile)
      .catch((e) => setError(`Couldn't load profile: ${String(e)}`));
  }, [userId, request]);

  async function messageThem() {
    if (!userId) return;
    setStarting(true);
    setError(null);
    try {
      const conv = await request<Conversation>(`/api/users/${userId}/dm`, {
        method: "POST",
      });
      nav(`/inbox/${conv.id}`);
    } catch (e) {
      setError(`Couldn't start DM: ${String(e)}`);
      setStarting(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!profile) return <p className="text-slate-500">Loading…</p>;

  const isSelf = clerkUser?.id === profile.id;

  return (
    <section className="space-y-6">
      <header className="flex items-center gap-4">
        {profile.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt=""
            className="h-20 w-20 rounded-full border border-slate-200 object-cover shrink-0"
          />
        ) : (
          <div className="h-20 w-20 rounded-full bg-slate-200 shrink-0" aria-hidden />
        )}
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold truncate">
            {profile.display_name}
            {isSelf && <span className="ml-2 text-base font-normal text-slate-500">(you)</span>}
          </h1>
          {isSelf ? (
            <Link
              to="/my-listings"
              className="mt-1 inline-block text-sm text-slate-600 underline"
            >
              Manage your listings →
            </Link>
          ) : (
            <button
              type="button"
              onClick={messageThem}
              disabled={starting}
              className="mt-2 rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
            >
              {starting ? "Starting…" : "Message me"}
            </button>
          )}
        </div>
      </header>

      <section>
        <h2 className="text-sm font-semibold mb-2">
          Active listings ({profile.active_listings.length})
        </h2>
        {profile.active_listings.length === 0 ? (
          <p className="text-slate-500 text-sm">No active listings right now.</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {profile.active_listings.map((l) => (
              <li key={l.id}>
                <Link
                  to={`/listings/${l.id}`}
                  className="block overflow-hidden rounded-lg border border-slate-200 bg-white hover:border-slate-400"
                >
                  {l.image_url && (
                    <img
                      src={l.image_url}
                      alt=""
                      className="w-full h-40 object-cover"
                      loading="lazy"
                    />
                  )}
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-medium truncate">{l.title}</p>
                        {l.category === "book" ? (
                          <>
                            <p className="text-sm text-slate-600 truncate">
                              {l.author ?? "Unknown author"}
                            </p>
                            {l.course && (
                              <p className="text-xs text-slate-500 mt-1">{l.course.code}</p>
                            )}
                          </>
                        ) : (
                          <p className="text-xs text-slate-500 capitalize mt-1">
                            {categoryLabel(l.category)}
                          </p>
                        )}
                      </div>
                      <p className="font-semibold shrink-0">
                        ${(l.price_cents / 100).toFixed(2)}
                      </p>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      Posted {formatRelativeDate(l.created_at)}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}

function categoryLabel(cat: string): string {
  return NON_BOOK_CATEGORIES.find((c) => c.value === cat)?.label ?? cat;
}
