import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useApi } from "../lib/api";
import type { Listing } from "../lib/types";
import { NON_BOOK_CATEGORIES } from "../lib/types";

type Tab = "books" | "everything-else";

/** Seller's home — listings I posted. Two tabs at the top split books
 *  from Everything Else so the visual treatment can differ (books are
 *  text-first; everything else shows thumbnails). State in `?tab=` so
 *  the URL is bookmarkable.
 */
export default function MyListings() {
  const { request } = useApi();
  const [params, setParams] = useSearchParams();
  const tab: Tab = params.get("tab") === "everything-else" ? "everything-else" : "books";

  const [listings, setListings] = useState<Listing[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<Listing[]>("/api/me/listings")
      .then(setListings)
      .catch((e) => setError(`Couldn't load your listings: ${String(e)}`));
  }, [request]);

  const books = useMemo(
    () => (listings ?? []).filter((l) => l.category === "book"),
    [listings],
  );
  const items = useMemo(
    () => (listings ?? []).filter((l) => l.category !== "book"),
    [listings],
  );

  function switchTab(t: Tab) {
    const next = new URLSearchParams(params);
    if (t === "everything-else") next.set("tab", "everything-else");
    else next.delete("tab");
    setParams(next);
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!listings) return <p className="text-slate-500">Loading…</p>;

  const visible = tab === "books" ? books : items;
  const sellLink = tab === "books" ? "/listings/new" : "/everything-else/new";
  const sellLabel = tab === "books" ? "+ Sell a book" : "+ List something";
  const emptyMsg =
    tab === "books"
      ? "You haven't posted any book listings yet."
      : "You haven't posted any general-marketplace items yet.";

  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">My listings</h1>
        <Link
          to={sellLink}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-white text-sm font-medium hover:bg-slate-800"
        >
          {sellLabel}
        </Link>
      </header>

      <nav className="border-b border-slate-200 flex gap-2 text-sm">
        <TabLink
          label={`Books (${books.length})`}
          active={tab === "books"}
          onClick={() => switchTab("books")}
        />
        <TabLink
          label={`Everything else (${items.length})`}
          active={tab === "everything-else"}
          onClick={() => switchTab("everything-else")}
        />
      </nav>

      {visible.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center">
          <p className="text-slate-600">{emptyMsg}</p>
          <Link to={sellLink} className="mt-2 inline-block text-sm underline">
            Post one →
          </Link>
        </div>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {visible.map((l) => {
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
                        {l.title}
                      </p>
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

function TabLink({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-2 -mb-px border-b-2 ${
        active
          ? "border-slate-900 font-semibold text-slate-900"
          : "border-transparent text-slate-600 hover:text-slate-900"
      }`}
    >
      {label}
    </button>
  );
}

function categoryLabel(cat: string): string {
  return NON_BOOK_CATEGORIES.find((c) => c.value === cat)?.label ?? cat;
}
