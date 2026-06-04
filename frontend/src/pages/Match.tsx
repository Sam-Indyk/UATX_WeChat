import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../lib/api";
import { formatRelativeDate } from "../lib/date";
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
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">For your courses</h1>
          <p className="text-sm text-slate-600">
            Ranked by how likely the seller's edition matches what your professor is using.
          </p>
        </div>
        {/* Persistent link to My classes — visible even when there ARE
            matches, so users can jump back any time to update their
            enrollment (per Sam's ask). */}
        <Link
          to="/my-classes"
          className="text-xs text-slate-500 hover:text-slate-900 underline shrink-0 mt-1"
        >
          Update my classes →
        </Link>
      </header>

      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!rows && !error && <p className="text-slate-500">Loading matches…</p>}
      {rows && rows.length === 0 && !error && (
        <p className="text-slate-500">
          No matches yet. Make sure you've set your current courses in{" "}
          <Link to="/my-classes" className="underline">My classes</Link>.
        </p>
      )}

      <ul className="space-y-3">
        {rows?.map((l) => (
          <li key={l.id}>
            <Link
              to={`/listings/${l.id}`}
              className="block rounded-lg border border-slate-200 bg-white p-4 transition-colors hover:border-slate-400 hover:shadow-sm"
            >
              <div className="flex justify-between gap-3">
                <div>
                  <p className="font-medium">{l.title}</p>
                  <p className="text-sm text-slate-600">{l.author}</p>
                  <p className="text-xs text-slate-500 mt-1 italic">{l.rationale}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-semibold">${(l.price_cents / 100).toFixed(2)}</p>
                  <p className="text-xs text-slate-500 capitalize">{l.condition.replace("_", " ")}</p>
                </div>
              </div>
              <p className="mt-2 text-xs text-slate-400">
                Posted {formatRelativeDate(l.created_at)}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
