import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../lib/api";
import type { MatchedListing } from "../lib/types";

export default function Match() {
  const { request } = useApi();
  const [rows, setRows] = useState<MatchedListing[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<MatchedListing[]>("/api/match")
      .then(setRows)
      .catch((e) => setError(`Couldn't load matches: ${String(e)}`));
  }, [request]);

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">For your courses</h1>
        <p className="text-sm text-slate-600">
          Ranked by how likely the seller's edition matches what your professor is using.
        </p>
      </header>

      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!rows && !error && <p className="text-slate-500">Loading matches…</p>}
      {rows && rows.length === 0 && !error && (
        <p className="text-slate-500">
          No matches yet. Make sure you've set your current courses in{" "}
          <Link to="/onboarding" className="underline">onboarding</Link>.
        </p>
      )}

      <ul className="space-y-3">
        {rows?.map((l) => (
          <li key={l.id}>
            <Link
              to={`/listings/${l.id}`}
              className="block rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400"
            >
              <div className="flex justify-between gap-3">
                <div>
                  <p className="font-medium">{l.book_title}</p>
                  <p className="text-sm text-slate-600">{l.book_author}</p>
                  <p className="text-xs text-slate-500 mt-1 italic">{l.rationale}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-semibold">${(l.price_cents / 100).toFixed(2)}</p>
                  <p className="text-xs text-slate-500 capitalize">{l.condition.replace("_", " ")}</p>
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
