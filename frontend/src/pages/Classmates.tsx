import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useApi } from "../lib/api";
import { useUnread } from "../hooks/useUnreadCount";
import ConversationThread from "../components/ConversationThread";
import type { Classmate, Conversation, EnrollmentKind } from "../lib/types";

const POLL_INTERVAL_MS = 15_000;

/** Color codes for the OTHER user's enrollment kind on a shared course.
 *  - current: emerald (active, "we share this right now")
 *  - past:    slate   (neutral, "they took it — likely have the book")
 *  - upcoming: sky    (future, "they will take it") */
const KIND_STYLES: Record<EnrollmentKind, string> = {
  current: "bg-emerald-100 text-emerald-800",
  past: "bg-slate-100 text-slate-700",
  upcoming: "bg-sky-100 text-sky-800",
};

function KindLabel({ kind }: { kind: EnrollmentKind }) {
  return (
    <span
      className={`inline-block shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${KIND_STYLES[kind]}`}
    >
      {kind}
    </span>
  );
}

/** Classmates page, post-IA-restructuring (PR #20).
 *
 *  Two-pane layout: list of classmates on the left, the selected DM
 *  thread on the right. Replaces the old grid-of-cards where clicking
 *  a classmate navigated to /inbox/:id.
 *
 *  Each row carries dm_conversation_id (null if no DM yet) and
 *  unread_count from the backend. Click → if no DM exists, POST to
 *  create one; either way, open the thread inline via ?dm=<id>.
 */
export default function Classmates() {
  const { request } = useApi();
  const { counts } = useUnread();
  // Trigger refetch when DM unread changes (new incoming, read elsewhere).
  const dmsBadge = counts.dms;

  const [params, setParams] = useSearchParams();
  const activeDmId = params.get("dm");

  const [classmates, setClassmates] = useState<Classmate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);

  const refetch = useCallback(() => {
    request<Classmate[]>("/api/classmates")
      .then((rows) => {
        setClassmates(rows);
        setError(null);
      })
      .catch((e) => setError(`Couldn't load classmates: ${String(e)}`));
  }, [request]);

  useEffect(() => {
    refetch();
    const id = setInterval(refetch, POLL_INTERVAL_MS);
    const onFocus = () => refetch();
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [refetch]);

  useEffect(() => {
    refetch();
  }, [dmsBadge, refetch]);

  async function openClassmate(c: Classmate) {
    if (opening) return;
    if (c.dm_conversation_id) {
      const next = new URLSearchParams(params);
      next.set("dm", c.dm_conversation_id);
      setParams(next);
      return;
    }
    // No DM yet — create one, then open it.
    setOpening(c.id);
    try {
      const conv = await request<Conversation>(`/api/users/${c.id}/dm`, { method: "POST" });
      const next = new URLSearchParams(params);
      next.set("dm", conv.id);
      setParams(next);
      refetch(); // pull the freshly-created dm_conversation_id onto the row
    } catch (e) {
      setError(`Couldn't start chat: ${String(e)}`);
    } finally {
      setOpening(null);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!classmates) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Classmates</h1>
        <p className="text-sm text-slate-600">
          Students who took, are taking, or will take one of your current classes — ranked
          by how many classes you share. Click anyone to chat.
        </p>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span>Color codes:</span>
          <KindLabel kind="current" />
          <KindLabel kind="past" />
          <KindLabel kind="upcoming" />
        </div>
      </header>

      {classmates.length === 0 && (
        <p className="text-slate-500">
          No classmates yet. Make sure you've set your current courses in{" "}
          <Link to="/my-classes" className="underline">My classes</Link>.
        </p>
      )}

      {classmates.length > 0 && (
        <div className="grid gap-4 md:grid-cols-[320px_1fr]">
          {/* Mobile: hide the list whenever a DM is open so the thread
              fills the screen. Back button below restores it. */}
          <ul className={`space-y-1 md:border-r md:border-slate-200 md:pr-3 ${activeDmId ? "hidden md:block" : ""}`}>
            {classmates.map((c) => {
              const isActive = c.dm_conversation_id !== null && c.dm_conversation_id === activeDmId;
              const isOpening = opening === c.id;
              const unread = c.unread_count;
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => openClassmate(c)}
                    disabled={isOpening || opening !== null}
                    className={`block w-full text-left rounded-md p-2 disabled:opacity-60 ${
                      isActive ? "bg-slate-100" : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {c.avatar_url ? (
                        <img
                          src={c.avatar_url}
                          alt=""
                          className="h-10 w-10 rounded-full object-cover shrink-0"
                        />
                      ) : (
                        <div className="h-10 w-10 rounded-full bg-slate-200 shrink-0" aria-hidden />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className={`truncate text-sm ${unread > 0 ? "font-semibold" : "font-medium"}`}>
                            {c.display_name}
                          </p>
                          {unread > 0 && (
                            <span className="shrink-0 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-semibold flex items-center justify-center">
                              {unread > 99 ? "99+" : unread}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500">
                          {c.shared_courses.length} shared course
                          {c.shared_courses.length === 1 ? "" : "s"}
                        </p>
                        <ul className="mt-1 space-y-0.5">
                          {c.shared_courses.map((sc) => (
                            <li
                              key={sc.id}
                              className="flex items-center gap-1.5 text-xs"
                            >
                              <KindLabel kind={sc.kind} />
                              <span className="text-slate-700 truncate flex-1 min-w-0">
                                {sc.title}
                              </span>
                              <span className="text-slate-400 shrink-0">{sc.code}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                    {isOpening && (
                      <p className="mt-1 text-xs text-slate-500">Opening chat…</p>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>

          <div className={`min-w-0 ${activeDmId ? "" : "hidden md:block"}`}>
            {activeDmId ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    const next = new URLSearchParams(params);
                    next.delete("dm");
                    setParams(next);
                  }}
                  className="md:hidden mb-3 inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
                >
                  ← Back to classmates
                </button>
                <ConversationThread conversationId={activeDmId} />
              </>
            ) : (
              <p className="text-slate-500 text-sm">
                Click a classmate on the left to start (or resume) a chat.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
