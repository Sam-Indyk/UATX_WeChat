import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiRequest } from "../lib/api";
import { formatRelativeDate } from "../lib/date";
import type { Listing, ListingCategory } from "../lib/types";
import { NON_BOOK_CATEGORIES } from "../lib/types";

/** General-marketplace browse — the "Everything Else" tab.
 *
 *  Only displays non-book listings WITH a photo (backend enforces both).
 *  Category dropdown + search input filter the results client-side.
 *  Each card shows the main image prominently because that's what
 *  the user is shopping by for furniture / electronics / etc.
 */
export default function EverythingElse() {
  const [listings, setListings] = useState<Listing[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [params, setParams] = useSearchParams();
  const cat = params.get("category") ?? "";
  const q = params.get("q") ?? "";

  useEffect(() => {
    setListings(null);
    setError(null);
    const qs = cat ? `?category=${encodeURIComponent(cat)}` : `?category=non-book`;
    apiRequest<Listing[]>(`/api/listings${qs}`)
      .then(setListings)
      .catch((e) => setError(`Couldn't load items: ${String(e)}`));
  }, [cat]);

  const filtered = useMemo(() => {
    if (!listings) return [];
    const lc = q.trim().toLowerCase();
    if (!lc) return listings;
    return listings.filter(
      (l) => l.title.toLowerCase().includes(lc) || l.description.toLowerCase().includes(lc),
    );
  }, [listings, q]);

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold">Everything else</h1>
          <p className="text-sm text-slate-600">
            Non-book stuff between UATX students — furniture, electronics, clothing, bikes,
            kitchen, whatever.
          </p>
        </div>
        <Link
          to="/everything-else/new"
          className="rounded-md bg-amber-600 px-3 py-1.5 text-white text-sm font-medium hover:bg-amber-700 shrink-0"
        >
          + List something
        </Link>
      </header>

      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="search"
          placeholder="Search items…"
          value={q}
          onChange={(e) => {
            const next = new URLSearchParams(params);
            const v = e.target.value;
            if (v) next.set("q", v);
            else next.delete("q");
            setParams(next);
          }}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          value={cat}
          onChange={(e) => {
            const next = new URLSearchParams(params);
            const v = e.target.value;
            if (v) next.set("category", v);
            else next.delete("category");
            setParams(next);
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          aria-label="Filter by category"
        >
          <option value="">All categories</option>
          {NON_BOOK_CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!listings && !error && <p className="text-slate-500">Loading…</p>}
      {listings && filtered.length === 0 && !error && (
        <p className="text-slate-500">No items match your filters.</p>
      )}

      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((l) => (
          <li key={l.id}>
            <Link
              to={`/listings/${l.id}`}
              className="block overflow-hidden rounded-lg border border-slate-200 bg-white transition-colors hover:border-slate-400 hover:shadow-sm"
            >
              {/* image is required for non-book listings, but we still
                  defend against null in case a listing was created
                  before this PR landed. */}
              {l.image_url ? (
                <img
                  src={l.image_url}
                  alt=""
                  className="w-full aspect-[4/3] object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="w-full aspect-[4/3] bg-slate-100" aria-hidden />
              )}
              <div className="p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium truncate">{l.title}</p>
                  <p className="font-semibold shrink-0">${(l.price_cents / 100).toFixed(2)}</p>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  <span className="capitalize">{categoryLabel(l.category)}</span>
                  <span className="mx-1">·</span>
                  <span className="capitalize">{l.condition.replace("_", " ")}</span>
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Posted {formatRelativeDate(l.created_at)}
                </p>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function categoryLabel(cat: ListingCategory): string {
  return NON_BOOK_CATEGORIES.find((c) => c.value === cat)?.label ?? cat;
}
