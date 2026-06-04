import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useApi } from "../lib/api";
import { useUnread } from "../hooks/useUnreadCount";
import ConversationThread from "../components/ConversationThread";
import type { Conversation } from "../lib/types";

const POLL_INTERVAL_MS = 15_000;

/** Buyer-side counterpart to /my-listings. Lists conversations on
 *  listings I'm chatting about as a buyer. Two-pane layout: convos on
 *  the left, selected thread on the right. State in ?conv= so the URL
 *  is bookmarkable.
 */
export default function MyInquiries() {
  const { request } = useApi();
  const { counts } = useUnread();
  const inquiriesBadge = counts.inquiries; // triggers refetch when changes

  const [params, setParams] = useSearchParams();
  const activeConvoId = params.get("conv");

  const [convos, setConvos] = useState<Conversation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(() => {
    request<Conversation[]>("/api/me/inquiries")
      .then((rows) => {
        setConvos(rows);
        setError(null);
      })
      .catch((e) => setError(`Couldn't load inquiries: ${String(e)}`));
  }, [request]);

  // Initial + interval + focus + react to unread badge changes.
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
  }, [inquiriesBadge, refetch]);

  function selectConvo(id: string | null) {
    const next = new URLSearchParams(params);
    if (id) next.set("conv", id);
    else next.delete("conv");
    setParams(next);
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!convos) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">My inquiries</h1>
        <p className="text-sm text-slate-600">
          Books you're chatting about with sellers. Click one to see the conversation.
        </p>
      </header>

      {convos.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center">
          <p className="text-slate-600">No conversations yet.</p>
          <p className="text-sm text-slate-500 mt-1">
            Find a book on Browse or For my courses and click "Message seller" to start one.
          </p>
        </div>
      )}

      {convos.length > 0 && (
        <div className="grid gap-4 md:grid-cols-[320px_1fr]">
          {/* Mobile: hide the list once a conversation is open so the
              thread fills the screen. Back button restores it. */}
          <ul className={`space-y-1 md:border-r md:border-slate-200 md:pr-3 ${activeConvoId ? "hidden md:block" : ""}`}>
            {convos.map((c) => {
              const isActive = c.id === activeConvoId;
              const unread = c.unread_count;
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => selectConvo(c.id)}
                    className={`block w-full text-left rounded-md p-2 ${
                      isActive ? "bg-slate-100" : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {c.listing?.image_url ? (
                        <img
                          src={c.listing.image_url}
                          alt=""
                          className="h-12 w-12 rounded-md object-cover border border-slate-200 shrink-0"
                        />
                      ) : (
                        <div className="h-12 w-12 rounded-md bg-slate-100 border border-slate-200 shrink-0" />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className={`truncate text-sm ${unread > 0 ? "font-semibold" : "font-medium"}`}>
                            {c.listing?.title ?? "Direct message"}
                          </p>
                          {unread > 0 && (
                            <span className="shrink-0 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-semibold flex items-center justify-center">
                              {unread > 99 ? "99+" : unread}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 truncate">
                          with {c.listing?.seller.display_name ?? c.other_user.display_name}
                        </p>
                      </div>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className={`min-w-0 ${activeConvoId ? "" : "hidden md:block"}`}>
            {activeConvoId ? (
              <>
                <button
                  type="button"
                  onClick={() => selectConvo(null)}
                  className="md:hidden mb-3 inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
                >
                  ← Back to inquiries
                </button>
                <ConversationThread conversationId={activeConvoId} />
              </>
            ) : (
              <p className="text-slate-500 text-sm">
                Pick a conversation on the left to read it.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
