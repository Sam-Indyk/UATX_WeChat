import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest, useApi } from "../lib/api";
import type { Course, Enrollment, EnrollmentKind } from "../lib/types";

// Defaults the user sees when they FIRST add a course of a given kind.
// If they're updating an existing enrollment (e.g. changing kind from
// current → past after a semester ends), we preserve the term they
// originally entered — see save() below.
const DEFAULT_TERM_BY_KIND: Record<EnrollmentKind, string> = {
  current: "Spring 2026",
  upcoming: "Fall 2026",
  past: "Fall 2025",
};

const CENTERS = [
  { prefix: "INF", label: "Intellectual Foundations" },
  { prefix: "ALT", label: "Arts and Letters" },
  { prefix: "EPH", label: "Economics, Politics, and History" },
  { prefix: "STM", label: "Science, Tech, Engineering, Math" },
  { prefix: "POL", label: "Polaris" },
  { prefix: "EDU", label: "Special Topics" },
];

type Selection = EnrollmentKind | "none";

export default function MyClasses() {
  const nav = useNavigate();
  const { request } = useApi();

  const [courses, setCourses] = useState<Course[] | null>(null);
  const [existing, setExisting] = useState<Enrollment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Map<string, Selection>>(new Map());
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [center, setCenter] = useState("");
  const [showOnlyEnrolled, setShowOnlyEnrolled] = useState(false);

  useEffect(() => {
    Promise.all([
      apiRequest<Course[]>("/api/courses"),
      request<Enrollment[]>("/api/me/enrollments"),
    ])
      .then(([c, e]) => {
        setCourses(c);
        setExisting(e);
        // Seed the selection map from existing enrollments.
        const m = new Map<string, Selection>();
        for (const enr of e) m.set(enr.course.id, enr.kind);
        setSelection(m);
      })
      .catch((e) => setError(`Couldn't load your classes: ${String(e)}`));
  }, [request]);

  function setKindFor(courseId: string, kind: Selection) {
    setSelection((prev) => {
      const next = new Map(prev);
      if (kind === "none") next.delete(courseId);
      else next.set(courseId, kind);
      return next;
    });
  }

  const filtered = useMemo(() => {
    if (!courses) return [];
    const q = search.trim().toLowerCase();
    return courses.filter((c) => {
      if (center && !c.code.startsWith(center + " ")) return false;
      if (showOnlyEnrolled && !selection.has(c.id)) return false;
      if (!q) return true;
      return c.code.toLowerCase().includes(q) || c.title.toLowerCase().includes(q);
    });
  }, [courses, search, center, showOnlyEnrolled, selection]);

  const counts = useMemo(() => {
    let current = 0, upcoming = 0, past = 0;
    for (const k of selection.values()) {
      if (k === "current") current++;
      else if (k === "upcoming") upcoming++;
      else if (k === "past") past++;
    }
    return { current, upcoming, past };
  }, [selection]);

  async function save() {
    if (!existing) return;
    setSaving(true);
    setError(null);
    try {
      const existingByCourse = new Map(existing.map((e) => [e.course.id, e]));

      // Upserts: any course that's selected (current/upcoming/past) and
      // either wasn't enrolled before or had a different kind.
      for (const [courseId, kind] of selection) {
        if (kind === "none") continue;
        const ex = existingByCourse.get(courseId);
        const term = ex ? ex.term : DEFAULT_TERM_BY_KIND[kind];
        if (!ex || ex.kind !== kind) {
          await request("/api/me/enrollments", {
            method: "POST",
            body: { course_id: courseId, term, kind },
          });
        }
      }

      // Deletes: any course that was enrolled but is no longer selected.
      for (const ex of existing) {
        if (!selection.has(ex.course.id)) {
          await request(`/api/me/enrollments/${ex.id}`, { method: "DELETE" });
        }
      }

      nav("/match");
    } catch (e) {
      setError(`Couldn't save: ${String(e)}`);
      setSaving(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!courses || !existing) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4 max-w-2xl">
      <header>
        <h1 className="text-2xl font-semibold">My classes</h1>
        <p className="text-sm text-slate-600">
          Which UATX courses you're <strong>taking now</strong> (so we can find your
          textbooks), <strong>about to take</strong> (so we can plan ahead), and <strong>already
          took</strong> (so we know you might have those books to sell). Come back any time to
          update — new semester, new class, dropped a class, etc.
        </p>
      </header>

      {courses.length === 0 && (
        <p className="text-amber-600 text-sm">
          No courses in the catalog. Something went wrong on the seed step — talk to Sam.
        </p>
      )}

      {courses.length > 0 && (
        <>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="search"
              placeholder="Search by code or title…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <select
              value={center}
              onChange={(e) => setCenter(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              aria-label="Filter by center"
            >
              <option value="">All centers</option>
              {CENTERS.map((c) => (
                <option key={c.prefix} value={c.prefix}>
                  {c.prefix} — {c.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {filtered.length} of {courses.length} ·{" "}
              <span className="font-medium text-slate-700">{counts.current}</span> current ·{" "}
              <span className="font-medium text-slate-700">{counts.upcoming}</span> upcoming ·{" "}
              <span className="font-medium text-slate-700">{counts.past}</span> past
            </span>
            <label className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={showOnlyEnrolled}
                onChange={(e) => setShowOnlyEnrolled(e.target.checked)}
              />
              Only show selected
            </label>
          </div>
        </>
      )}

      <ul className="space-y-1">
        {filtered.map((c) => {
          const current = selection.get(c.id) ?? "none";
          return (
            <li
              key={c.id}
              className="flex items-center gap-3 rounded-md border border-slate-200 bg-white px-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm">
                  <span className="font-medium">{c.code}</span>
                  <span className="text-slate-600 ml-2">{c.title}</span>
                </p>
              </div>
              <select
                value={current}
                onChange={(e) => setKindFor(c.id, e.target.value as Selection)}
                className={`shrink-0 rounded-md border px-2 py-1 text-xs ${
                  current === "none"
                    ? "border-slate-300 text-slate-500"
                    : "border-slate-400 text-slate-900 font-medium"
                }`}
                aria-label={`Enrollment for ${c.code}`}
              >
                <option value="none">Not enrolled</option>
                <option value="current">Current</option>
                <option value="upcoming">Upcoming</option>
                <option value="past">Past</option>
              </select>
            </li>
          );
        })}
      </ul>

      {courses.length > 0 && filtered.length === 0 && (
        <p className="text-slate-500 text-sm">No courses match your filters.</p>
      )}

      <button
        onClick={save}
        disabled={saving}
        className="rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save and continue"}
      </button>
    </section>
  );
}
