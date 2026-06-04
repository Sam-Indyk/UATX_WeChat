import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../lib/api";

type Category = "feature" | "bug" | "other";

const CATEGORIES: { value: Category; label: string }[] = [
  { value: "feature", label: "Feature request" },
  { value: "bug", label: "Bug report" },
  { value: "other", label: "Other / general feedback" },
];

/** Lets users submit ideas, bug reports, or general feedback. Lands in
 *  the feedback_submissions table — no moderation UI yet, teammates
 *  read via Supabase. */
export default function Feedback() {
  const { request } = useApi();

  const [category, setCategory] = useState<Category>("feature");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = body.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      await request("/api/feedback", {
        method: "POST",
        body: { category, body: trimmed },
      });
      setSubmitted(true);
    } catch (e) {
      setError(`Couldn't submit: ${String(e)}`);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <section className="max-w-lg space-y-4">
        <header>
          <h1 className="text-2xl font-semibold">Thanks!</h1>
          <p className="text-sm text-slate-600">
            We read every submission. If you've got more ideas, send them along.
          </p>
        </header>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => {
              setBody("");
              setSubmitted(false);
            }}
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Submit another
          </button>
          <Link
            to="/"
            className="rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700"
          >
            Back home
          </Link>
        </div>
      </section>
    );
  }

  return (
    <form onSubmit={onSubmit} className="max-w-lg space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Submit an idea</h1>
        <p className="text-sm text-slate-600">
          Tell us what you'd like to see. We're a small team building this for UATX,
          and the next features come straight from this form.
        </p>
      </header>

      <label className="block">
        <span className="block text-sm font-medium mb-1">Type</span>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as Category)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="block text-sm font-medium mb-1">What's on your mind?</span>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          required
          maxLength={4000}
          rows={6}
          placeholder="A study-group chat for each class would be great…"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <span className="block text-xs text-slate-500 mt-1">
          {body.length} / 4000
        </span>
      </label>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <button
        type="submit"
        disabled={submitting || !body.trim()}
        className="rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
      >
        {submitting ? "Sending…" : "Send"}
      </button>
    </form>
  );
}
