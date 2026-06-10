import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../lib/api";
import { formatRelativeDate } from "../lib/date";
import type { FeedbackSubmissionAdmin, User } from "../lib/types";

const CATEGORY_STYLES: Record<FeedbackSubmissionAdmin["category"], string> = {
  feature: "bg-sky-100 text-sky-800",
  bug: "bg-red-100 text-red-800",
  other: "bg-slate-100 text-slate-700",
};

/** Admin-only view of every feedback submission. The backend gates the
 *  endpoint via require_admin (ADMIN_EMAILS env-var allowlist). We
 *  ALSO check /api/me's is_admin client-side so non-admins see a clear
 *  403 page instead of the network-error fallback. */
export default function AdminFeedback() {
  const { request } = useApi();

  const [me, setMe] = useState<User | null>(null);
  const [rows, setRows] = useState<FeedbackSubmissionAdmin[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<User>("/api/me")
      .then((u) => {
        setMe(u);
        if (u.is_admin) {
          return request<FeedbackSubmissionAdmin[]>("/api/admin/feedback").then(setRows);
        }
      })
      .catch((e) => setError(`Couldn't load: ${String(e)}`));
  }, [request]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!me) return <p className="text-slate-500">Loading…</p>;

  if (!me.is_admin) {
    return (
      <section className="max-w-md mx-auto text-center py-12 space-y-4">
        <h1 className="text-2xl font-semibold">Not an admin</h1>
        <p className="text-slate-600">
          This page is restricted to the team. If you think you should have access,
          message Eitan or Sam.
        </p>
        <Link
          to="/"
          className="inline-block rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700"
        >
          Back home
        </Link>
      </section>
    );
  }

  if (!rows) return <p className="text-slate-500">Loading submissions…</p>;

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Feedback inbox</h1>
        <p className="text-sm text-slate-600">
          All submissions across all users, newest first. {rows.length} total.
        </p>
      </header>

      {rows.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-slate-500">
          No feedback yet.
        </p>
      )}

      <ul className="space-y-3">
        {rows.map((row) => (
          <li
            key={row.id}
            className="rounded-lg border border-slate-200 bg-white p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${CATEGORY_STYLES[row.category]}`}
              >
                {row.category}
              </span>
              <span className="text-xs text-slate-500">
                {formatRelativeDate(row.created_at)}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-800 whitespace-pre-wrap break-words">
              {row.body}
            </p>
            <p className="mt-2 text-xs text-slate-500">
              From:{" "}
              {row.user_display_name ? (
                <>
                  <span className="font-medium text-slate-700">{row.user_display_name}</span>
                  {row.user_email && (
                    <span className="text-slate-500"> · {row.user_email}</span>
                  )}
                </>
              ) : (
                <span className="italic text-slate-400">deleted user</span>
              )}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
