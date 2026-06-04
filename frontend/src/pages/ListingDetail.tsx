import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { SignedIn, SignedOut, useUser } from "@clerk/clerk-react";
import { apiRequest, useApi } from "../lib/api";
import type { Conversation, Enrollment, EnrollmentKind, Listing } from "../lib/types";
import { PAYMENT_METHODS } from "../lib/types";

const VIEWER_KIND_LABEL: Record<EnrollmentKind, string> = {
  current: "You're in this class now",
  past: "You took this class",
  upcoming: "You're signed up for this class",
};

const VIEWER_KIND_STYLES: Record<EnrollmentKind, string> = {
  current: "bg-emerald-100 text-emerald-800 border-emerald-200",
  past: "bg-slate-100 text-slate-700 border-slate-200",
  upcoming: "bg-sky-100 text-sky-800 border-sky-200",
};

export default function ListingDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { request } = useApi();
  const { user } = useUser();
  const [params] = useSearchParams();
  // Set by Stripe when redirecting the buyer back from the hosted
  // checkout page. The listing's actual status change happens server-
  // side via webhook, so this is just for the UI banner.
  const stripeResult = params.get("stripe");

  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [contacting, setContacting] = useState(false);
  const [paying, setPaying] = useState(false);
  // Set if the signed-in viewer is enrolled in the listing's course
  // (any kind). Drives the "You're in this class" chip. Fetched lazily
  // after the listing loads so we don't block on a second request.
  const [viewerKind, setViewerKind] = useState<EnrollmentKind | null>(null);

  useEffect(() => {
    if (!id) return;
    apiRequest<Listing>(`/api/listings/${id}`)
      .then(setListing)
      .catch((e) => setError(`Couldn't load listing: ${String(e)}`));
  }, [id]);

  // Check if the signed-in viewer is enrolled in this listing's course.
  // Silent on failure — the chip is optional polish, not load-bearing.
  useEffect(() => {
    if (!listing?.course || !user) {
      setViewerKind(null);
      return;
    }
    const courseId = listing.course.id;
    apiRequest<Enrollment[]>("/api/me/enrollments")
      .then((enrollments) => {
        const found = enrollments.find((e) => e.course.id === courseId);
        setViewerKind(found?.kind ?? null);
      })
      .catch(() => setViewerKind(null));
  }, [listing, user]);

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

  async function payWithStripe() {
    if (!id) return;
    setPaying(true);
    setError(null);
    try {
      const { url } = await request<{ url: string }>(
        `/api/listings/${id}/checkout`,
        { method: "POST" },
      );
      // Hard redirect — Stripe's hosted checkout takes over, then sends
      // the buyer back to /listings/:id?stripe=success or ?stripe=cancel.
      window.location.href = url;
    } catch (e) {
      setError(`Couldn't start checkout: ${String(e)}`);
      setPaying(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!listing) return <p className="text-slate-500">Loading…</p>;

  const isOwn = user?.id === listing.seller.id;
  const sellerAcceptsStripe = listing.payment_methods.includes("stripe");
  const sellerReadyForStripe = listing.seller.stripe_onboarded;
  const canPayWithStripe =
    !isOwn &&
    listing.status === "active" &&
    sellerAcceptsStripe &&
    sellerReadyForStripe;

  return (
    <article className="space-y-4">
      {stripeResult === "success" && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          ✓ Payment received. The seller will be notified and the listing
          is now reserved — message them to arrange pickup.
        </div>
      )}
      {stripeResult === "cancel" && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          Payment canceled. You can try again, or message the seller to
          arrange a different payment method.
        </div>
      )}

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
            {viewerKind && (
              <span
                className={`inline-flex items-center gap-1 mt-2 rounded-md border px-2 py-1 text-xs font-medium ${VIEWER_KIND_STYLES[viewerKind]}`}
              >
                <span aria-hidden>🎓</span>
                {VIEWER_KIND_LABEL[viewerKind]}
              </span>
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
        Seller:{" "}
        <Link
          to={`/users/${listing.seller.id}`}
          className="text-slate-700 underline hover:text-slate-900"
        >
          {listing.seller.display_name}
        </Link>
        {user?.id === listing.seller.id && (
          <span className="ml-1 text-slate-500">(you)</span>
        )}
      </p>

      <SignedIn>
        {isOwn ? (
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
          <div className="flex flex-wrap items-center gap-2">
            {canPayWithStripe && (
              <button
                onClick={payWithStripe}
                disabled={paying}
                className="rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
              >
                {paying ? "Starting Stripe…" : "Pay with Stripe"}
              </button>
            )}
            <button
              onClick={contactSeller}
              disabled={contacting || listing.status !== "active"}
              className={
                canPayWithStripe
                  ? // Secondary when Pay with Stripe is the primary
                    "rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                  : "rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
              }
            >
              {contacting ? "Starting…" : "Message seller"}
            </button>
          </div>
        )}
      </SignedIn>
      <SignedOut>
        <p className="text-sm text-slate-500">Sign in to message the seller.</p>
      </SignedOut>
    </article>
  );
}
