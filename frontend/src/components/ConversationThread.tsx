import { FormEvent, useEffect, useRef, useState } from "react";
import { useUser } from "@clerk/clerk-react";
import { useApi } from "../lib/api";
import { useUnread } from "../hooks/useUnreadCount";
import type { Message } from "../lib/types";

type Props = {
  conversationId: string;
  /** Optional header — caller controls how the thread is labeled
   *  ("Chat with Sam", "About Republic", etc.) since context differs
   *  by where the component is mounted. */
  header?: React.ReactNode;
};

/** Local-only flag on messages we've added optimistically (before the
 *  server confirmed). Kept inside this file so the shared Message type
 *  stays a pure server-shape representation. */
type LocalMessage = Message & { _pending?: boolean };

/** How often we poll for new messages while the thread is open. The
 *  silver "real-time-ish" requirement is <=5s end-to-end; polling every
 *  4s keeps us safely under that even with a slow round-trip. */
const POLL_INTERVAL_MS = 4_000;

/** A single conversation's message thread + send box.
 *
 *  Real-time-ish updates: while the thread is mounted, we re-fetch the
 *  messages list every 4 seconds and append any IDs we haven't seen.
 *  We picked polling over SSE/WebSockets because (a) the existing chat
 *  HTTP endpoint is already the source of truth, (b) Railway's free
 *  tier doesn't love long-lived connections, (c) it composes trivially
 *  with the existing useUnread polling, and (d) the 4s cadence is
 *  imperceptible for chat at this scale.
 *
 *  Optimistic send: when the user hits Send, we add the message to the
 *  list immediately with a temp id + `_pending` flag. The POST request
 *  then either swaps the temp message for the server one, or — on
 *  failure — removes the temp and restores the input so the user can
 *  retry without re-typing.
 */
export default function ConversationThread({ conversationId, header }: Props) {
  const { user } = useUser();
  const { request } = useApi();
  const { refetch: refetchUnread } = useUnread();

  const [messages, setMessages] = useState<LocalMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [body, setBody] = useState("");

  // Auto-scroll only when the user is already at (or near) the bottom,
  // so reading older history isn't yanked.
  const listRef = useRef<HTMLUListElement | null>(null);
  const lastScrollHeightRef = useRef<number>(0);

  // Append new messages from the server, skipping ones we already have
  // (by id). Used by both the initial load and the polling loop.
  function mergeIncoming(rows: Message[]) {
    setMessages((prev) => {
      if (!prev) return rows;
      const known = new Set(prev.map((m) => m.id));
      const toAdd = rows.filter((m) => !known.has(m.id));
      if (toAdd.length === 0) return prev;
      return [...prev, ...toAdd];
    });
  }

  useEffect(() => {
    setMessages(null);
    setError(null);

    let cancelled = false;

    async function loadOnce() {
      try {
        const rows = await request<Message[]>(`/api/conversations/${conversationId}/messages`);
        if (cancelled) return;
        // Initial load REPLACES (no merge) so we get a clean baseline.
        setMessages((prev) => (prev === null ? rows : prev));
        // Subsequent polls merge — handled below.
      } catch (e) {
        if (cancelled) return;
        setError(`Couldn't load messages: ${String(e)}`);
      }
    }

    async function pollOnce() {
      try {
        const rows = await request<Message[]>(`/api/conversations/${conversationId}/messages`);
        if (cancelled) return;
        mergeIncoming(rows);
        // If any of the freshly-arrived messages were from the other
        // party, they're effectively "read" right now since the thread
        // is open. Tell the server + refresh the nav badge so it
        // doesn't sit on a stale count.
        const incoming = rows.some((m) => m.sender_id !== user?.id && m.read_at === null);
        if (incoming) {
          request<{ marked_read: number }>(
            `/api/conversations/${conversationId}/read`,
            { method: "POST" },
          )
            .then(() => refetchUnread())
            .catch(() => {});
        }
      } catch {
        // silent — keep what we have
      }
    }

    loadOnce();

    // Mark-as-read fire-and-forget at mount, then refresh the nav badge
    // so it drops immediately (existing behavior from PR #13).
    request<{ marked_read: number }>(`/api/conversations/${conversationId}/read`, {
      method: "POST",
    })
      .then(() => refetchUnread())
      .catch(() => {});

    const id = setInterval(pollOnce, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [conversationId, request, refetchUnread, user?.id]);

  // Auto-scroll on new messages, but only when the user is near the
  // bottom (within 80px). Avoids snapping them away from older history.
  useEffect(() => {
    const el = listRef.current;
    if (!el || !messages) return;
    const nearBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < 80 ||
      lastScrollHeightRef.current === 0;
    if (nearBottom) {
      el.scrollTop = el.scrollHeight;
    }
    lastScrollHeightRef.current = el.scrollHeight;
  }, [messages]);

  async function send(e: FormEvent) {
    e.preventDefault();
    const text = body.trim();
    if (!text) return;

    setBody(""); // clear input immediately — snappy feel
    setError(null);

    // Optimistic: append a pending message before the request lands.
    const tempId = `temp-${crypto.randomUUID()}`;
    const optimistic: LocalMessage = {
      id: tempId,
      conversation_id: conversationId,
      sender_id: user?.id ?? "",
      body: text,
      created_at: new Date().toISOString(),
      read_at: null,
      _pending: true,
    };
    setMessages((prev) => (prev ? [...prev, optimistic] : [optimistic]));

    try {
      const real = await request<Message>(
        `/api/conversations/${conversationId}/messages`,
        { method: "POST", body: { body: text } },
      );
      // Swap the temp for the server version. The polling loop might
      // have already added the real one — dedupe in that case.
      setMessages((prev) => {
        if (!prev) return [real];
        const withoutTemp = prev.filter((m) => m.id !== tempId);
        if (withoutTemp.some((m) => m.id === real.id)) return withoutTemp;
        return [...withoutTemp, real];
      });
    } catch (e) {
      // Rollback: remove the optimistic message, restore the input so
      // the user can fix-and-retry without re-typing.
      setMessages((prev) => prev?.filter((m) => m.id !== tempId) ?? null);
      setBody(text);
      setError(`Couldn't send: ${String(e)}`);
    }
  }

  if (error && !messages) return <p className="text-red-600 text-sm">{error}</p>;
  if (!messages) return <p className="text-slate-500 text-sm">Loading…</p>;

  return (
    <div className="space-y-4">
      {header}
      <ul ref={listRef} className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
        {messages.length === 0 && (
          <li className="text-slate-500 text-sm">No messages yet — send one to start.</li>
        )}
        {messages.map((m) => {
          const mine = m.sender_id === user?.id;
          return (
            <li key={m.id} className={`flex flex-col ${mine ? "items-end" : "items-start"}`}>
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  mine ? "bg-slate-900 text-white" : "bg-white border border-slate-200"
                } ${m._pending ? "opacity-70" : ""}`}
              >
                {m.body}
              </div>
              {m._pending && (
                <span className="text-[10px] text-slate-400 italic mt-0.5">Sending…</span>
              )}
            </li>
          );
        })}
      </ul>

      {error && <p className="text-red-600 text-xs">{error}</p>}

      <form onSubmit={send} className="flex gap-2">
        <input
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Type a message…"
          maxLength={2000}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={!body.trim()}
          className="rounded-md bg-slate-900 px-4 py-2 text-white text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
