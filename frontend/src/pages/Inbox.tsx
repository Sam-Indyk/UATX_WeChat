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
          // Pick whichever party isn't me.
          const other = c.buyer.id === user?.id ? c.other_user : c.buyer;
          const isDM = c.listing === null;
          const title = isDM ? "Direct message" : c.listing!.book_title;
          // Tag the conversation kind on the right so people can tell DMs
          // and listing chats apart at a glance.
          const tag = isDM
            ? "DM"
            : c.buyer.id === user?.id
            ? "Buying"
            : "Selling";
          const unread = c.unread_count;
          return (
            <li key={c.id}>
              <Link
                to={`/inbox/${c.id}`}
                className={`block rounded-lg border bg-white p-3 hover:border-slate-400 ${
                  unread > 0 ? "border-slate-400" : "border-slate-200"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className={`truncate ${unread > 0 ? "font-semibold" : "font-medium"}`}>
                      {title}
                    </p>
                    <p className="text-sm text-slate-600">with {other.display_name}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {unread > 0 && (
                      <span
                        className="min-w-[20px] h-[20px] px-1.5 rounded-full bg-red-500 text-white text-[11px] font-semibold flex items-center justify-center"
                        aria-label={`${unread} unread`}
                      >
                        {unread > 99 ? "99+" : unread}
                      </span>
                    )}
                    <p className="text-xs text-slate-500">{tag}</p>
                  </div>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
