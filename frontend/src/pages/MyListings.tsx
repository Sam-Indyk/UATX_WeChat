import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../lib/api";
import type { Listing } from "../lib/types";

export default function MyListings() {
  const { request } = useApi();
  const [listings, setListings] = useState<Listing[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<Listing[]>("/api/me/listings")
      .then(setListings)
      .catch((e) => setError(`Couldn't load your listings: ${String(e)}`));
  }, [request]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!listings) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">My listings</h1>
        <Link
          to="/listings/new"
          className="rounded-md bg-slate-900 px-3 py-1.5 text-white text-sm font-medium hover:bg-slate-800"
        >
          + Sell a book
        </Link>
      </header>

      {listings.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center">
          <p className="text-slate-600">You haven't posted any listings yet.</p>
          <Link to="/listings/new" className="mt-2 inline-block text-sm underline">
            Post your first one →
          </Link>
        </div>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {listings.map((l) => {
          const unread = l.unread_count;
          return (
            <li key={l.id}>
              <Link
                to={`/my-listings/${l.id}`}
                className={`block overflow-hidden rounded-lg border bg-white hover:border-slate-400 ${
                  unread > 0 ? "border-slate-400" : "border-slate-200"
                }`}
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
                      <p className={`truncate ${unread > 0 ? "font-semibold" : "font-medium"}`}>
                        {l.book_title}
                      </p>
                      <p className="text-sm text-slate-600 truncate">{l.book_author}</p>
                      {l.course && (
                        <p className="text-xs text-slate-500 mt-1">{l.course.code}</p>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <p className="font-semibold">${(l.price_cents / 100).toFixed(2)}</p>
                      <p className="text-xs text-slate-500 capitalize">{l.status}</p>
                    </div>
                  </div>

                  {unread > 0 && (
                    <p className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-red-500 px-2 py-0.5 text-white text-xs font-semibold">
                      <span>{unread}</span>
                      <span>new {unread === 1 ? "message" : "messages"}</span>
                    </p>
                  )}
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
