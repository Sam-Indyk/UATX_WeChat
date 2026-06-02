import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { useApi } from "../lib/api";
import ConversationThread from "../components/ConversationThread";
import type { Conversation } from "../lib/types";

/** The existing standalone /inbox/:id page. Kept around so old links
 *  still work; will be deprecated when /inbox itself goes away in the
 *  IA-restructuring follow-up PRs. The actual thread UI now lives in
 *  the reusable ConversationThread component.
 */
export default function ConversationPage() {
  const { id } = useParams();
  const { user } = useUser();
  const { request } = useApi();

  const [conv, setConv] = useState<Conversation | null>(null);

  useEffect(() => {
    if (!id) return;
    request<Conversation[]>("/api/conversations")
      .then((rows) => setConv(rows.find((c) => c.id === id) ?? null))
      .catch(() => {});
  }, [id, request]);

  if (!id) return null;

  const otherParty = conv
    ? conv.buyer.id === user?.id
      ? conv.other_user
      : conv.buyer
    : null;

  const header = (
    <header>
      <h1 className="text-xl font-semibold">
        {otherParty ? `Chat with ${otherParty.display_name}` : "Conversation"}
      </h1>
      {conv?.listing && (
        <p className="text-sm text-slate-600">About {conv.listing.title}</p>
      )}
    </header>
  );

  return (
    <section className="max-w-xl">
      <ConversationThread conversationId={id} header={header} />
    </section>
  );
}
