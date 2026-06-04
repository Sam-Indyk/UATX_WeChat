import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { SignedIn, SignedOut, useUser } from "@clerk/clerk-react";
import { apiRequest, useApi } from "../lib/api";
import { formatRelativeDate } from "../lib/date";
import type {
  Conversation,
  Enrollment,
  EnrollmentKind,
  Listing,
  PublicUser,
} from "../lib/types";
import { PAYMENT_METHODS } from "../lib/types";

// Cap on the "More from this seller" preview. The seller's profile page
// (`/users/:id`) shows the full list; this row is a glance.
const SELLER_OTHER_PREVIEW_CAP = 3;

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
  // Other active listings from the same seller. Capped to a small
  // preview; the seller's profile page has the full list.
  const [otherFromSeller, setOtherFromSeller] = useState<Listing[]>([]);
  const [sellerTotalActive, setSellerTotalActive] = useState(0);

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

  // Fetch the seller's other active listings for the "More from this
  // seller" section. Reuses /api/users/:id which already returns the
  // full active_listings array. Silent on failure.
  useEffect(() => {
    if (!listing) {
      setOtherFromSeller([]);
      setSellerTotalActive(0);
      return;
    }
    const currentId = listing.id;
    apiRequest<PublicUser>(`/api/users/${listing.seller.id}`)
      .then((profile) => {
        const others = profile.active_listings.filter((l) => l.id !== currentId);
        setSellerTotalActive(others.length);
        setOtherFromSeller(others.slice(0, SELLER_OTHER_PREVIEW_CAP));
      })
      .catch(() => {
        setOtherFromSeller([]);
        setSellerTotalActive(0);
      });
  }, [listing]);

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

      {otherFromSeller.length > 0 && (
        <section className="pt-6 border-t border-slate-200">
          <div className="flex items-baseline justify-between gap-2 mb-3">
            <h2 className="text-sm font-semibold">
              More from {listing.seller.display_name}
            </h2>
            {sellerTotalActive > SELLER_OTHER_PREVIEW_CAP && (
              <Link
                to={`/users/${listing.seller.id}`}
                className="text-xs text-slate-500 underline hover:text-slate-900"
              >
                See all {sellerTotalActive} →
              </Link>
            )}
          </div>
          <ul className="grid gap-3 sm:grid-cols-3">
            {otherFromSeller.map((other) => (
              <li key={other.id}>
                <Link
                  to={`/listings/${other.id}`}
                  className="block overflow-hidden rounded-lg border border-slate-200 bg-white transition-colors hover:border-slate-400 hover:shadow-sm"
                >
                  {other.image_url && (
                    <img
                      src={other.image_url}
                      alt=""
                      className="w-full h-28 object-cover"
                      loading="lazy"
                    />
                  )}
                  <div className="p-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium truncate">{other.title}</p>
                      <p className="text-sm font-semibold shrink-0">
                        ${(other.price_cents / 100).toFixed(2)}
                      </p>
                    </div>
                    {other.category === "book" && other.author && (
                      <p className="text-xs text-slate-500 truncate mt-0.5">
                        {other.author}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-slate-400">
                      Posted {formatRelativeDate(other.created_at)}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
