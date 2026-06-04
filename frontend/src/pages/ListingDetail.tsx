import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { SignedIn, SignedOut, useUser } from "@clerk/clerk-react";
import { apiRequest, useApi } from "../lib/api";
import type { Conversation, Listing } from "../lib/types";
import { PAYMENT_METHODS } from "../lib/types";

export default function ListingDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { request } = useApi();
  const { user } = useUser();

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
      <header>
        <h1 className="text-2xl font-semibold">{listing.title}</h1>
        {listing.category === "book" ? (
          <>
            <p className="text-slate-600">
              {listing.author ?? "Unknown author"}
              {listing.edition ? ` — ${listing.edition}` : ""}
            </p>
            {listing.course && (
              <p className="text-sm text-slate-500">
                {listing.course.code} · {listing.course.title}
              </p>
            )}
          </>
        ) : (
          <p className="text-sm text-slate-500 capitalize">{listing.category}</p>
        )}
      </header>

      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
        <span>Price: <span className="font-medium">${(listing.price_cents / 100).toFixed(2)}</span></span>
        <span>Condition: <span className="font-medium capitalize">{listing.condition.replace("_", " ")}</span></span>
        <span>Status: <span className="font-medium capitalize">{listing.status}</span></span>
      </div>

      {/* Payment methods the seller said they accept. Order matches the
          canonical order in PAYMENT_METHODS (cash → venmo → zelle → paypal
          → stripe), regardless of how the seller saved them. Hidden when
          empty — no "Accepts: nothing" line. */}
      {listing.payment_methods.length > 0 && (
        <p className="text-sm text-slate-600">
          <span className="font-medium">Accepts:</span>{" "}
          {PAYMENT_METHODS.filter((pm) => listing.payment_methods.includes(pm.value))
            .map((pm) => pm.label)
            .join(" · ")}
        </p>
      )}

      {listing.description && (
        <p className="text-slate-700 whitespace-pre-wrap">{listing.description}</p>
      )}

      {listing.image_url && (
        <figure>
          <img
            src={listing.image_url}
            alt={`Photo of ${listing.title}`}
            className="w-full max-w-xl rounded-lg border border-slate-200 object-contain"
            // eslint-disable-next-line no-console
            onError={(e) => {
              // If Supabase Storage returns a 4xx (bucket not public, wrong
              // key, etc.) the <img> just shows a broken icon. Surface it
              // in DevTools so future-debug-Sam knows where to look.
              console.warn("Listing image failed to load:", listing.image_url, e);
            }}
          />
        </figure>
      )}

      <p className="text-sm text-slate-600">
        Seller: {listing.seller.display_name}
        {user?.id === listing.seller.id && (
          <span className="ml-1 text-slate-500">(you)</span>
        )}
      </p>

      <SignedIn>
        {user?.id === listing.seller.id ? (
          // Self-listing — backend rejects /contact with a 400, and
          // the "Message seller" CTA reads as weird when you ARE the
          // seller. Surface a path to the seller-side management view.
          <Link
            to={`/my-listings/${listing.id}`}
            className="inline-block rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Manage in My listings →
          </Link>
        ) : (
          <button
            onClick={contactSeller}
            disabled={contacting || listing.status !== "active"}
            className="rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
          >
            {contacting ? "Starting…" : "Message seller"}
          </button>
        )}
      </SignedIn>
      <SignedOut>
        <p className="text-sm text-slate-500">Sign in to message the seller.</p>
      </SignedOut>
    </article>
  );
}
