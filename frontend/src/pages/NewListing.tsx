import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest, useApi } from "../lib/api";
import type { Course, Listing } from "../lib/types";

const CONDITIONS = ["new", "like_new", "good", "fair", "poor"] as const;

export default function NewListing() {
  const nav = useNavigate();
  const { request } = useApi();

  const [courses, setCourses] = useState<Course[] | null>(null);
  const [coursesError, setCoursesError] = useState<string | null>(null);

  const [courseId, setCourseId] = useState("");
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [edition, setEdition] = useState("");
  const [condition, setCondition] = useState<typeof CONDITIONS[number]>("good");
  const [priceCents, setPriceCents] = useState(1500);
  const [description, setDescription] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Course[]>("/api/courses").then(setCourses).catch((e) =>
      setCoursesError(`Couldn't load courses: ${String(e)}`),
    );
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const listing = await request<Listing>("/api/listings", {
        method: "POST",
        body: {
          course_id: courseId || null,
          book_title: title,
          book_author: author,
          book_edition: edition || null,
          condition,
          price_cents: priceCents,
          description,
        },
      });
      nav(`/listings/${listing.id}`);
    } catch (e) {
      setError(`Couldn't create listing: ${String(e)}`);
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4 max-w-lg">
      <h1 className="text-2xl font-semibold">Sell a book</h1>

      <Field label="Course (optional)">
        {coursesError && <p className="text-red-600 text-sm">{coursesError}</p>}
        <select
          value={courseId}
          onChange={(e) => setCourseId(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">— none —</option>
          {courses?.map((c) => (
            <option key={c.id} value={c.id}>{c.code} — {c.title}</option>
          ))}
        </select>
      </Field>

      <Field label="Book title">
        <input
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          maxLength={200}
        />
      </Field>

      <Field label="Author">
        <input
          required
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          maxLength={200}
        />
      </Field>

      <Field label="Edition (optional)">
        <input
          value={edition}
          onChange={(e) => setEdition(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          maxLength={40}
        />
      </Field>

      <Field label="Condition">
        <select
          value={condition}
          onChange={(e) => setCondition(e.target.value as typeof CONDITIONS[number])}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm capitalize"
        >
          {CONDITIONS.map((c) => (
            <option key={c} value={c} className="capitalize">{c.replace("_", " ")}</option>
          ))}
        </select>
      </Field>

      <Field label="Price (USD)">
        <input
          type="number"
          required
          min={0}
          step="0.01"
          value={(priceCents / 100).toFixed(2)}
          onChange={(e) => setPriceCents(Math.round(parseFloat(e.target.value || "0") * 100))}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </Field>

      <Field label="Description">
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={2000}
          rows={4}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </Field>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-slate-900 px-4 py-2 text-white text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
      >
        {submitting ? "Posting…" : "Post listing"}
      </button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-sm font-medium mb-1">{label}</span>
      {children}
    </label>
  );
}
