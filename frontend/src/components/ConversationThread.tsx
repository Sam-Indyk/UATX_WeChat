import { FormEvent, useEffect, useState } from "react";
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

/** A single conversation's message thread + send box. Extracted from the
 *  old standalone Conversation page so the new /my-listings chat subtab
 *  can render it inline without a route change.
 *
 *  On mount: loads messages, fires mark-as-read, force-refreshes the
 *  nav badge so it drops immediately instead of waiting for the next
 *  30s poll.
 */
export default function ConversationThread({ conversationId, header }: Props) {
  const { user } = useUser();
  const { request } = useApi();
  const { refetch: refetchUnread } = useUnread();

  const [messages, setMessages] = useState<Message[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    setMessages(null);
    setError(null);
    request<Message[]>(`/api/conversations/${conversationId}/messages`)
      .then(setMessages)
      .catch((e) => setError(`Couldn't load messages: ${String(e)}`));
    request<{ marked_read: number }>(`/api/conversations/${conversationId}/read`, {
      method: "POST",
    })
      .then(() => refetchUnread())
      .catch(() => {});
  }, [conversationId, request, refetchUnread]);

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setSending(true);
    try {
      const msg = await request<Message>(
        `/api/conversations/${conversationId}/messages`,
        { method: "POST", body: { body: body.trim() } },
      );
      setMessages((prev) => (prev ? [...prev, msg] : [msg]));
      setBody("");
    } catch (e) {
      setError(`Couldn't send: ${String(e)}`);
    } finally {
      setSending(false);
    }
  }

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!messages) return <p className="text-slate-500 text-sm">Loading…</p>;

  return (
    <div className="space-y-4">
      {header}
      <ul className="space-y-2">
        {messages.length === 0 && (
          <li className="text-slate-500 text-sm">No messages yet — send one to start.</li>
        )}
        {messages.map((m) => {
          const mine = m.sender_id === user?.id;
          return (
            <li
              key={m.id}
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                mine ? "ml-auto bg-slate-900 text-white" : "bg-white border border-slate-200"
              }`}
            >
              {m.body}
            </li>
          );
        })}
      </ul>

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
          disabled={sending || !body.trim()}
          className="rounded-md bg-slate-900 px-4 py-2 text-white text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {sending ? "Sending…" : "Send"}
        </button>
      </form>
    </div>
  );
}
