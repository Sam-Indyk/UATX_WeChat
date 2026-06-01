import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useApi } from "../lib/api";
import ConversationThread from "../components/ConversationThread";
import ListingSettingsForm from "../components/ListingSettingsForm";
import type { Conversation, Listing } from "../lib/types";

/** Single listing the signed-in user owns, with two subtabs:
 *
 *    - Chat: list of buyers who messaged about this listing, click one
 *            to see their thread inline.
 *    - Settings: edit listing fields, change status, upload/replace photo.
 *
 *  Subtab state is in the URL as a query param so refresh + back button
 *  keep you where you were.
 *
 *    /my-listings/:id                       → Chat tab, no buyer selected
 *    /my-listings/:id?tab=chat&conv=<cid>   → Chat tab, that buyer open
 *    /my-listings/:id?tab=settings          → Settings tab
 */
export default function MyListingDetail() {
  const { id } = useParams();
  const { request } = useApi();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "settings" ? "settings" : "chat";
  const activeConvoId = params.get("conv");

  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refetchListing = useCallback(() => {
    if (!id) return;
    request<Listing>(`/api/listings/${id}`)
      .then(setListing)
      .catch((e) => setError(`Couldn't load listing: ${String(e)}`));
  }, [id, request]);

  useEffect(() => {
    refetchListing();
  }, [refetchListing]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!listing || !id) return <p className="text-slate-500">Loading…</p>;

  return (
    <section className="space-y-4">
      <header className="flex items-start gap-3">
        {listing.image_url && (
          <img
            src={listing.image_url}
            alt=""
            className="h-16 w-16 rounded-md object-cover border border-slate-200 shrink-0"
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs">
            <Link to="/my-listings" className="text-slate-500 hover:text-slate-900">
              ← My listings
            </Link>
            <span className="text-slate-400">·</span>
            <span className="text-slate-500 capitalize">{listing.status}</span>
          </div>
          <h1 className="text-2xl font-semibold mt-1">{listing.book_title}</h1>
          <p className="text-sm text-slate-600">{listing.book_author}</p>
        </div>
      </header>

      {/* Subtab nav */}
      <nav className="border-b border-slate-200 flex gap-2 text-sm">
        <SubtabLink
          label="Chat"
          active={tab === "chat"}
          onClick={() => {
            // Drop ?conv when switching back to chat-no-selection.
            const next = new URLSearchParams(params);
            next.delete("tab");
            next.delete("conv");
            setParams(next);
          }}
        />
        <SubtabLink
          label="Settings"
          active={tab === "settings"}
          onClick={() => {
            const next = new URLSearchParams(params);
            next.set("tab", "settings");
            next.delete("conv");
            setParams(next);
          }}
        />
      </nav>

      {tab === "chat" ? (
        <ChatSubtab
          listingId={id}
          activeConvoId={activeConvoId}
          onSelectConvo={(cid) => {
            const next = new URLSearchParams(params);
            if (cid) next.set("conv", cid);
            else next.delete("conv");
            setParams(next);
          }}
        />
      ) : (
        <ListingSettingsForm listing={listing} onChange={refetchListing} />
      )}
    </section>
  );
}

function SubtabLink({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-2 -mb-px border-b-2 ${
        active
          ? "border-slate-900 font-semibold text-slate-900"
          : "border-transparent text-slate-600 hover:text-slate-900"
      }`}
    >
      {label}
    </button>
  );
}

function ChatSubtab({
  listingId,
  activeConvoId,
  onSelectConvo,
}: {
  listingId: string;
  activeConvoId: string | null;
  onSelectConvo: (id: string | null) => void;
}) {
  const { request } = useApi();
  const [convos, setConvos] = useState<Conversation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<Conversation[]>(`/api/listings/${listingId}/conversations`)
      .then(setConvos)
      .catch((e) => setError(`Couldn't load buyer messages: ${String(e)}`));
  }, [listingId, request]);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!convos) return <p className="text-slate-500 text-sm">Loading buyers…</p>;

  if (convos.length === 0) {
    return (
      <p className="text-slate-500 text-sm">
        No buyers have messaged yet. When they do, they'll show up here.
      </p>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-[260px_1fr]">
      <ul className="space-y-1 border-r border-slate-200 pr-3">
        {convos.map((c) => {
          const unread = c.unread_count;
          const isActive = c.id === activeConvoId;
          return (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => onSelectConvo(c.id)}
                className={`block w-full text-left rounded-md px-3 py-2 ${
                  isActive ? "bg-slate-100" : "hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className={`truncate text-sm ${unread > 0 ? "font-semibold" : ""}`}>
                    {c.buyer.display_name}
                  </p>
                  {unread > 0 && (
                    <span className="shrink-0 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-semibold flex items-center justify-center">
                      {unread > 99 ? "99+" : unread}
                    </span>
                  )}
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="min-w-0">
        {activeConvoId ? (
          <ConversationThread conversationId={activeConvoId} />
        ) : (
          <p className="text-slate-500 text-sm">
            Pick a buyer on the left to see your conversation.
          </p>
        )}
      </div>
    </div>
  );
}
