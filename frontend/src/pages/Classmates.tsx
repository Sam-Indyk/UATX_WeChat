import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "../lib/api";
import type { Classmate, Conversation } from "../lib/types";

export default function Classmates() {
  const { request } = useApi();
  const navigate = useNavigate();
  const [data, setData] = useState<Classmate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Track which classmate's "Start chat" is in flight so we can disable
  // just that one and avoid double-clicks creating two open requests.
  const [opening, setOpening] = useState<string | null>(null);

  useEffect(() => {
    request<Classmate[]>("/api/classmates")
      .then(setData)
      .catch((e) => setError(`Couldn't load classmates: ${String(e)}`));
  }, [request]);

  async function startChat(classmateId: string) {
    if (opening) return;
    setOpening(classmateId);
    try {
      const conv = await request<Conversation>(`/api/users/${classmateId}/dm`, {
        method: "POST",
      });
      navigate(`/inbox/${conv.id}`);
    } catch (e) {
      setError(`Couldn't start chat: ${String(e)}`);
      setOpening(null);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Classmates</h1>
        <p className="text-sm text-slate-600">
          Other UATX students enrolled in your current courses, ranked by how many of your
          classes you share.
        </p>
      </header>

      {data.length === 0 && (
        <p className="text-slate-500">
          No classmates yet. Make sure you've set your current courses in{" "}
          <Link to="/onboarding" className="underline">onboarding</Link>.
        </p>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {data.map((c) => {
          const isOpening = opening === c.id;
          return (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => startChat(c.id)}
                disabled={isOpening || opening !== null}
                className="w-full text-left rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400 disabled:opacity-60"
              >
                <div className="flex items-center gap-3">
                  {c.avatar_url ? (
                    <img
                      src={c.avatar_url}
                      alt=""
                      className="h-10 w-10 rounded-full object-cover"
                    />
                  ) : (
                    <div className="h-10 w-10 rounded-full bg-slate-200" aria-hidden />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="font-medium truncate">{c.display_name}</p>
                    <p className="text-xs text-slate-500">
                      {c.shared_courses.length} shared course
                      {c.shared_courses.length === 1 ? "" : "s"}
                    </p>
                  </div>
                  <span className="text-xs text-slate-600 shrink-0">
                    {isOpening ? "Opening…" : "Chat"}
                  </span>
                </div>
                <ul className="mt-3 space-y-1">
                  {c.shared_courses.map((sc) => (
                    <li key={sc.id} className="text-sm text-slate-700">
                      {sc.title}
                      <span className="text-xs text-slate-400 ml-1.5">{sc.code}</span>
                    </li>
                  ))}
                </ul>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
