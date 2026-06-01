import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../lib/api";
import type { Classmate } from "../lib/types";

export default function Classmates() {
  const { request } = useApi();
  const [data, setData] = useState<Classmate[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<Classmate[]>("/api/classmates")
      .then(setData)
      .catch((e) => setError(`Couldn't load classmates: ${String(e)}`));
  }, [request]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Classmates</h1>
        <p className="text-sm text-slate-600">
          Other UATX students enrolled in at least one of your current courses.
        </p>
      </header>

      {data.length === 0 && (
        <p className="text-slate-500">
          No classmates yet. Make sure you've set your current courses in{" "}
          <Link to="/onboarding" className="underline">onboarding</Link>.
        </p>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {data.map((c) => (
          <li
            key={c.id}
            className="rounded-lg border border-slate-200 bg-white p-4"
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
              <p className="font-medium">{c.display_name}</p>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {c.shared_courses.map((sc) => (
                <span
                  key={sc.id}
                  title={sc.title}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
                >
                  {sc.code}
                </span>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
