import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest, useApi } from "../lib/api";
import type { Course, Enrollment } from "../lib/types";

const DEFAULT_TERM = "Spring 2026";

const CENTERS = [
  { prefix: "INF", label: "Intellectual Foundations" },
  { prefix: "ALT", label: "Arts and Letters" },
  { prefix: "EPH", label: "Economics, Politics, and History" },
  { prefix: "STM", label: "Science, Tech, Engineering, Math" },
  { prefix: "POL", label: "Polaris" },
  { prefix: "EDU", label: "Special Topics" },
];

export default function Onboarding() {
  const nav = useNavigate();
  const { request } = useApi();

  const [courses, setCourses] = useState<Course[] | null>(null);
  const [existing, setExisting] = useState<Enrollment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [center, setCenter] = useState("");

  const filtered = useMemo(() => {
    if (!courses) return [];
    const q = search.trim().toLowerCase();
    return courses.filter((c) => {
      if (center && !c.code.startsWith(center + " ")) return false;
      if (!q) return true;
      return c.code.toLowerCase().includes(q) || c.title.toLowerCase().includes(q);
    });
  }, [courses, search, center]);

  useEffect(() => {
    Promise.all([
      apiRequest<Course[]>("/api/courses"),
      request<Enrollment[]>("/api/me/enrollments"),
    ])
      .then(([c, e]) => {
        setCourses(c);
        setExisting(e);
        setSelected(new Set(e.filter((row) => row.is_current).map((row) => row.course.id)));
      })
      .catch((e) => setError(`Couldn't load onboarding data: ${String(e)}`));
  }, [request]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const already = new Set((existing ?? []).map((e) => e.course.id));
      const toAdd = Array.from(selected).filter((id) => !already.has(id));
      for (const id of toAdd) {
        await request("/api/me/enrollments", {
          method: "POST",
          body: { course_id: id, term: DEFAULT_TERM, is_current: true },
        });
      }
      nav("/match");
    } catch (e) {
      setError(`Couldn't save: ${String(e)}`);
      setSaving(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!courses) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4 max-w-lg">
      <header>
        <h1 className="text-2xl font-semibold">Pick your current courses</h1>
        <p className="text-sm text-slate-600">
          We'll use these to surface textbook listings from upperclassmen who took the same courses.
        </p>
      </header>

      {courses.length === 0 && (
        <p className="text-amber-600 text-sm">
          No courses in the catalog yet. A teammate needs to seed the <code>courses</code> table —
          see the runway in CLAUDE.md.
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

          <p className="text-xs text-slate-500">
            Showing {filtered.length} of {courses.length} courses · {selected.size} selected
          </p>
        </>
      )}

      <ul className="space-y-1.5">
        {filtered.map((c) => (
          <li key={c.id}>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selected.has(c.id)}
                onChange={() => toggle(c.id)}
              />
              <span className="text-sm"><span className="font-medium">{c.code}</span> — {c.title}</span>
            </label>
          </li>
        ))}
      </ul>

      {courses.length > 0 && filtered.length === 0 && (
        <p className="text-slate-500 text-sm">No courses match your search.</p>
      )}

      <button
        onClick={save}
        disabled={saving || selected.size === 0}
        className="rounded-md bg-slate-900 px-4 py-2 text-white text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save and continue"}
      </button>
    </section>
  );
}
