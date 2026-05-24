import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { useApi } from "../lib/api";
import type { Conversation } from "../lib/types";

export default function Inbox() {
  const { user } = useUser();
  const { request } = useApi();
  const [convs, setConvs] = useState<Conversation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<Conversation[]>("/api/conversations")
      .then(setConvs)
      .catch((e) => setError(`Couldn't load inbox: ${String(e)}`));
  }, [request]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!convs) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Inbox</h1>
      {convs.length === 0 && <p className="text-slate-500">No conversations yet.</p>}
      <ul className="space-y-2">
        {convs.map((c) => {
          const iAmBuyer = c.buyer.id === user?.id;
          const otherName = iAmBuyer ? c.listing.seller.display_name : c.buyer.display_name;
          return (
            <li key={c.id}>
              <Link
                to={`/inbox/${c.id}`}
                className="block rounded-lg border border-slate-200 bg-white p-3 hover:border-slate-400"
              >
                <div className="flex justify-between">
                  <div>
                    <p className="font-medium">{c.listing.book_title}</p>
                    <p className="text-sm text-slate-600">with {otherName}</p>
                  </div>
                  <p className="text-xs text-slate-500">{iAmBuyer ? "Buying" : "Selling"}</p>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
