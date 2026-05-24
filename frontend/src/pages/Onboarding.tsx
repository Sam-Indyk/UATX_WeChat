import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest, useApi } from "../lib/api";
import type { Course, Enrollment } from "../lib/types";

const DEFAULT_TERM = "Spring 2026";

export default function Onboarding() {
  const nav = useNavigate();
  const { request } = useApi();

  const [courses, setCourses] = useState<Course[] | null>(null);
  const [existing, setExisting] = useState<Enrollment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

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

      <ul className="space-y-1.5">
        {courses.map((c) => (
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
