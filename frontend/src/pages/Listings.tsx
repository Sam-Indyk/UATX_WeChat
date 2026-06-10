import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { SignedIn } from "@clerk/clerk-react";
import { apiRequest, useApi } from "../lib/api";
import CourseSearchPicker from "../components/CourseSearchPicker";
import { formatRelativeDate } from "../lib/date";
import type { Course, Listing } from "../lib/types";

type SortOption = "newest" | "low" | "high";

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "low", label: "Price: low to high" },
  { value: "high", label: "Price: high to low" },
];

export default function Listings() {
  const [params, setParams] = useSearchParams();
  const { request } = useApi();
  const courseFilter = params.get("course_id") ?? "";
  const queryParam = params.get("q") ?? "";
  const sortParam = (params.get("sort") as SortOption) || "newest";
  // ?mine=1 → backend filters to listings whose course is in the
  // viewer's current/upcoming enrollments. Replaces the old /match
  // route as a filter on this page instead of its own tab.
  const myCoursesOnly = params.get("mine") === "1";

  // Mirror the URL ?q= into a local input value so typing feels instant
  // without writing to the URL on every keystroke. We push to the URL
  // on a 300ms debounce so the fetch doesn't fire mid-keystroke.
  const [searchInput, setSearchInput] = useState(queryParam);

  const [courses, setCourses] = useState<Course[] | null>(null);
  const [listings, setListings] = useState<Listing[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Update URL params when the typed term settles.
  useEffect(() => {
    const handle = setTimeout(() => {
      if (searchInput === queryParam) return;
      const next = new URLSearchParams(params);
      if (searchInput.trim()) next.set("q", searchInput.trim());
      else next.delete("q");
      setParams(next, { replace: true });
    }, 300);
    return () => clearTimeout(handle);
  }, [searchInput, queryParam, params, setParams]);

  useEffect(() => {
    apiRequest<Course[]>("/api/courses")
      .then(setCourses)
      .catch((e) => setError(`Couldn't load courses: ${String(e)}`));
  }, []);

  useEffect(() => {
    setListings(null);
    setError(null);
    const qs = new URLSearchParams({ category: "book" });
    if (courseFilter) qs.set("course_id", courseFilter);
    if (queryParam) qs.set("q", queryParam);
    if (myCoursesOnly) qs.set("my_courses", "true");
    // my_courses needs the Clerk JWT (backend 401s without it). Use
    // the auth'd helper when filtering by mine; fall back to the
    // anonymous helper otherwise so signed-out users can browse.
    const fetcher = myCoursesOnly ? request : apiRequest;
    fetcher<Listing[]>(`/api/listings?${qs.toString()}`)
      .then(setListings)
      .catch((e) => setError(`Couldn't load listings: ${String(e)}`));
  }, [courseFilter, queryParam, myCoursesOnly, request]);

  // Frontend-side sort. The backend already orders by created_at desc,
  // so "newest" is a no-op. Price sorts are in-memory — cheap at any
  // realistic scale, and lets us re-sort without a refetch.
  const sortedListings = useMemo(() => {
    if (!listings) return null;
    if (sortParam === "low") {
      return [...listings].sort((a, b) => a.price_cents - b.price_cents);
    }
    if (sortParam === "high") {
      return [...listings].sort((a, b) => b.price_cents - a.price_cents);
    }
    return listings;
  }, [listings, sortParam]);

  function changeSort(s: SortOption) {
    const next = new URLSearchParams(params);
    if (s === "newest") next.delete("sort");
    else next.set("sort", s);
    setParams(next, { replace: true });
  }

  function toggleMyCourses() {
    const next = new URLSearchParams(params);
    if (myCoursesOnly) next.delete("mine");
    else next.set("mine", "1");
    setParams(next, { replace: true });
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold shrink-0">Books</h1>
        <SignedIn>
          <Link
            to="/listings/new"
            className="shrink-0 rounded-md bg-amber-600 px-3 py-1.5 text-white text-sm font-medium hover:bg-amber-700 whitespace-nowrap"
          >
            + Sell a book
          </Link>
        </SignedIn>
      </div>

      {/* Filters row */}
      <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto_auto] sm:items-center">
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by title or author…"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <CourseSearchPicker
          courses={courses ?? []}
          selectedId={courseFilter || null}
          onChange={(id) => {
            const next = new URLSearchParams(params);
            if (id) next.set("course_id", id);
            else next.delete("course_id");
            setParams(next, { replace: true });
          }}
          placeholder="Filter by course…"
          allowEmpty
          emptyLabel="All courses"
        />
        <select
          value={sortParam}
          onChange={(e) => changeSort(e.target.value as SortOption)}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm bg-white"
        >
          {SORT_OPTIONS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <SignedIn>
          <button
            type="button"
            onClick={toggleMyCourses}
            className={
              myCoursesOnly
                ? "rounded-md bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700 whitespace-nowrap"
                : "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
            }
            aria-pressed={myCoursesOnly}
          >
            {myCoursesOnly ? "✓ My courses" : "My courses"}
          </button>
        </SignedIn>
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!listings && !error && <p className="text-slate-500">Loading listings…</p>}
      {sortedListings && sortedListings.length === 0 && !error && (
        <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
          <p className="text-slate-600">
            {queryParam || courseFilter || myCoursesOnly
              ? myCoursesOnly && !queryParam && !courseFilter
                ? "No books match courses you're enrolled in. Add your classes in My classes, or browse all listings."
                : "No listings match your filters."
              : "No book listings yet — be the first to sell one."}
          </p>
          {(queryParam || courseFilter || myCoursesOnly) && (
            <button
              type="button"
              onClick={() => setParams({}, { replace: true })}
              className="mt-2 text-sm underline text-slate-600"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {sortedListings?.map((l) => (
          <li key={l.id}>
            <Link
              to={`/listings/${l.id}`}
              className="block rounded-lg border border-slate-200 bg-white p-4 transition-colors hover:border-slate-400 hover:shadow-sm"
            >
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
              <p className="mt-2 text-xs text-slate-400">
                by <span className="text-slate-600">{l.seller.display_name}</span>
                <span className="mx-1">·</span>
                Posted {formatRelativeDate(l.created_at)}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
