import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiRequest } from "../lib/api";
import type { Course, Listing } from "../lib/types";

export default function Listings() {
  const [params, setParams] = useSearchParams();
  const courseFilter = params.get("course_id") ?? "";

  const [courses, setCourses] = useState<Course[] | null>(null);
  const [listings, setListings] = useState<Listing[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Course[]>("/api/courses").then(setCourses).catch((e) =>
      setError(`Couldn't load courses: ${String(e)}`),
    );
  }, []);

  useEffect(() => {
    setListings(null);
    setError(null);
    const qs = courseFilter ? `?course_id=${encodeURIComponent(courseFilter)}` : "";
    apiRequest<Listing[]>(`/api/listings${qs}`)
      .then(setListings)
      .catch((e) => setError(`Couldn't load listings: ${String(e)}`));
  }, [courseFilter]);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Listings</h1>
        <select
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          value={courseFilter}
          onChange={(e) => {
            const v = e.target.value;
            if (v) setParams({ course_id: v });
            else setParams({});
          }}
        >
          <option value="">All courses</option>
          {courses?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} — {c.title}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!listings && !error && <p className="text-slate-500">Loading listings…</p>}
      {listings && listings.length === 0 && !error && (
        <p className="text-slate-500">No listings yet.</p>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {listings?.map((l) => (
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
              <div className="flex justify-between gap-2 p-4">
                <div>
                  <p className="font-medium">{l.book_title}</p>
                  <p className="text-sm text-slate-600">{l.book_author}</p>
                  {l.course && (
                    <p className="text-xs text-slate-500 mt-1">{l.course.code}</p>
                  )}
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
