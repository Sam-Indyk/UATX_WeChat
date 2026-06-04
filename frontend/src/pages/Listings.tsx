import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiRequest } from "../lib/api";
import CourseSearchPicker from "../components/CourseSearchPicker";
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
    // Browse is the BOOKS-only home now. Non-books live in /everything-else.
    const params = new URLSearchParams({ category: "book" });
    if (courseFilter) params.set("course_id", courseFilter);
    apiRequest<Listing[]>(`/api/listings?${params.toString()}`)
      .then(setListings)
      .catch((e) => setError(`Couldn't load listings: ${String(e)}`));
  }, [courseFilter]);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold shrink-0">Listings</h1>
        <div className="w-full sm:w-auto sm:max-w-xs sm:flex-1">
          <CourseSearchPicker
            courses={courses ?? []}
            selectedId={courseFilter || null}
            onChange={(id) => (id ? setParams({ course_id: id }) : setParams({}))}
            placeholder="Filter by course…"
            allowEmpty
            emptyLabel="All courses"
          />
        </div>
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
              className="block rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400"
            >
              {/* No inline image on Browse — books are recognizable by
                  title + author + course. Click into the listing to
                  see the cover photo (if any). Per Sam's spec. */}
              <div className="flex justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium truncate">{l.title}</p>
                  <p className="text-sm text-slate-600 truncate">{l.author ?? "Unknown author"}</p>
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
