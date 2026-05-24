import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { useApi } from "../lib/api";
import type { Message } from "../lib/types";

export default function ConversationPage() {
  const { id } = useParams();
  const { user } = useUser();
  const { request } = useApi();

  const [messages, setMessages] = useState<Message[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!id) return;
    request<Message[]>(`/api/conversations/${id}/messages`)
      .then(setMessages)
      .catch((e) => setError(`Couldn't load messages: ${String(e)}`));
  }, [id, request]);

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!id || !body.trim()) return;
    setSending(true);
    try {
      const msg = await request<Message>(`/api/conversations/${id}/messages`, {
        method: "POST",
        body: { body: body.trim() },
      });
      setMessages((prev) => (prev ? [...prev, msg] : [msg]));
      setBody("");
    } catch (e) {
      setError(`Couldn't send: ${String(e)}`);
    } finally {
      setSending(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!messages) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4 max-w-xl">
      <h1 className="text-xl font-semibold">Conversation</h1>
      <ul className="space-y-2">
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
    </section>
  );
}
