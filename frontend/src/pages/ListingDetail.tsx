import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { SignedIn, SignedOut } from "@clerk/clerk-react";
import { apiRequest, useApi } from "../lib/api";
import type { Conversation, Listing } from "../lib/types";

export default function ListingDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { request } = useApi();

  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [contacting, setContacting] = useState(false);

  useEffect(() => {
    if (!id) return;
    apiRequest<Listing>(`/api/listings/${id}`)
      .then(setListing)
      .catch((e) => setError(`Couldn't load listing: ${String(e)}`));
  }, [id]);

  async function contactSeller() {
    if (!id) return;
    setContacting(true);
    setError(null);
    try {
      const conv = await request<Conversation>(`/api/listings/${id}/contact`, { method: "POST" });
      nav(`/inbox/${conv.id}`);
    } catch (e) {
      setError(`Couldn't start conversation: ${String(e)}`);
      setContacting(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!listing) return <p className="text-slate-500">Loading…</p>;

  return (
    <article className="space-y-4">
      {listing.image_url && (
        <img
          src={listing.image_url}
          alt=""
          className="w-full max-w-md rounded-lg border border-slate-200 object-cover"
        />
      )}
      <header>
        <h1 className="text-2xl font-semibold">{listing.book_title}</h1>
        <p className="text-slate-600">{listing.book_author}{listing.book_edition ? ` — ${listing.book_edition}` : ""}</p>
        {listing.course && <p className="text-sm text-slate-500">{listing.course.code} · {listing.course.title}</p>}
      </header>

      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
        <span>Price: <span className="font-medium">${(listing.price_cents / 100).toFixed(2)}</span></span>
        <span>Condition: <span className="font-medium capitalize">{listing.condition.replace("_", " ")}</span></span>
        <span>Status: <span className="font-medium capitalize">{listing.status}</span></span>
      </div>

      {listing.description && (
        <p className="text-slate-700 whitespace-pre-wrap">{listing.description}</p>
      )}

      <p className="text-sm text-slate-600">Seller: {listing.seller.display_name}</p>

      <SignedIn>
        <button
          onClick={contactSeller}
          disabled={contacting || listing.status !== "active"}
          className="rounded-md bg-slate-900 px-4 py-2 text-white text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {contacting ? "Starting…" : "Message seller"}
        </button>
      </SignedIn>
      <SignedOut>
        <p className="text-sm text-slate-500">Sign in to message the seller.</p>
      </SignedOut>
    </article>
  );
}
