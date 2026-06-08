import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useApi } from "../lib/api";
import { STRIPE_ENABLED } from "../lib/feature-flags";
import type { User } from "../lib/types";

export default function Settings() {
  const { request } = useApi();
  const [params] = useSearchParams();
  // Set when the user just came back from Stripe-hosted onboarding. The
  // server-side flag flips via webhook (account.updated), which arrives
  // independently, so we just nudge users to refresh if they don't see
  // the connected pill yet.
  const justReturnedFromStripe = params.get("stripe") === "return";

  const [me, setMe] = useState<User | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Avatar upload state.
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);

  // Stripe Connect state.
  const [stripeStarting, setStripeStarting] = useState(false);
  const [stripeError, setStripeError] = useState<string | null>(null);

  async function startStripeOnboarding() {
    setStripeStarting(true);
    setStripeError(null);
    try {
      const { onboarding_url } = await request<{ onboarding_url: string }>(
        "/api/me/stripe/onboard",
        { method: "POST" },
      );
      // Redirect to the Stripe-hosted form. They'll come back to
      // /settings?stripe=return when done (or ?stripe=refresh if the
      // link expired mid-flow).
      window.location.href = onboarding_url;
    } catch (e) {
      setStripeError(`Couldn't start Stripe onboarding: ${String(e)}`);
      setStripeStarting(false);
    }
  }

  useEffect(() => {
    request<User>("/api/me")
      .then((u) => {
        setMe(u);
        setDisplayName(u.display_name);
      })
      .catch((e) => setLoadError(`Couldn't load your profile: ${String(e)}`));
  }, [request]);

  async function save(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      const updated = await request<User>("/api/me", {
        method: "PATCH",
        body: { display_name: displayName.trim() },
      });
      setMe(updated);
      setDisplayName(updated.display_name);
      setSaved(true);
    } catch (e) {
      setSaveError(`Couldn't save: ${String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  async function uploadAvatar(e: FormEvent) {
    e.preventDefault();
    if (!avatarFile) return;
    setAvatarUploading(true);
    setAvatarError(null);
    try {
      const fd = new FormData();
      fd.append("file", avatarFile);
      const updated = await request<User>("/api/me/avatar", {
        method: "POST",
        body: fd,
      });
      setMe(updated);
      setAvatarFile(null);
    } catch (e) {
      setAvatarError(`Couldn't upload: ${String(e)}`);
    } finally {
      setAvatarUploading(false);
    }
  }

  if (loadError) return <p className="text-red-600">{loadError}</p>;
  if (!me) return <p className="text-slate-500">Loading…</p>;

  const trimmed = displayName.trim();
  const unchanged = trimmed === me.display_name;
  // Hide the placeholder email synthesized by auth.py when Clerk's JWT
  // doesn't carry a real email claim. Showing "user_xyz@clerk.local"
  // confuses people — they think it's their actual address.
  const isPlaceholderEmail = me.email.endsWith("@clerk.local");

  return (
    <section className="space-y-8 max-w-md">
      <header>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-slate-600">
          How you appear to other students in chats, listings, and the classmates view.
        </p>
      </header>

      {/* Avatar */}
      <section>
        <h2 className="text-sm font-semibold mb-2">Profile picture</h2>
        <div className="flex items-center gap-4">
          {me.avatar_url ? (
            <img
              src={me.avatar_url}
              alt=""
              className="h-20 w-20 rounded-full border border-slate-200 object-cover"
            />
          ) : (
            <div className="h-20 w-20 rounded-full bg-slate-200" aria-hidden />
          )}
          <form onSubmit={uploadAvatar} className="flex-1 space-y-2">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="user"
              onChange={(e) => {
                setAvatarError(null);
                setAvatarFile(e.target.files?.[0] ?? null);
              }}
              className="text-sm w-full"
            />
            <button
              type="submit"
              disabled={!avatarFile || avatarUploading}
              className="rounded-md bg-amber-600 px-3 py-1.5 text-white text-xs font-medium hover:bg-amber-700 disabled:opacity-50"
            >
              {avatarUploading ? "Uploading…" : "Upload"}
            </button>
            {avatarError && <p className="text-red-600 text-xs">{avatarError}</p>}
            <p className="text-xs text-slate-500">JPEG, PNG, or WebP, up to 5 MB.</p>
          </form>
        </div>
      </section>

      <hr />

      {/* Stripe payments */}
      <section>
        <h2 className="text-sm font-semibold mb-2">Stripe payments</h2>
        <p className="text-xs text-slate-500 mb-3">
          Connect a Stripe account to accept card payments on your listings.
          Buyers will see a "Pay with Stripe" button on any listing where you've
          checked Stripe in the payment methods.
        </p>
        {!STRIPE_ENABLED ? (
          <>
            <button
              type="button"
              disabled
              className="rounded-md bg-slate-300 px-3 py-1.5 text-slate-600 text-xs font-medium cursor-not-allowed"
            >
              Connect with Stripe
            </button>
            <p className="mt-2 text-xs text-slate-500">
              In-app Stripe payments are coming soon. For now, arrange payments
              with the buyer directly (cash, Venmo, Zelle, PayPal).
            </p>
          </>
        ) : me.stripe_onboarded ? (
          <div className="flex items-center gap-2 text-sm text-emerald-700">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" aria-hidden />
            Connected. You can accept Stripe payments.
          </div>
        ) : (
          <>
            {justReturnedFromStripe && (
              <p className="mb-3 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800">
                Welcome back from Stripe. It can take a moment for the
                connection to register — refresh this page in a few seconds
                to see the green "Connected" pill.
              </p>
            )}
            <button
              type="button"
              onClick={startStripeOnboarding}
              disabled={stripeStarting}
              className="rounded-md bg-amber-600 px-3 py-1.5 text-white text-xs font-medium hover:bg-amber-700 disabled:opacity-50"
            >
              {stripeStarting ? "Redirecting…" : "Connect with Stripe"}
            </button>
            {stripeError && <p className="mt-2 text-red-600 text-xs">{stripeError}</p>}
          </>
        )}
      </section>

      <hr />

      {/* Display name + email */}
      <form onSubmit={save} className="space-y-4">
        <label className="block">
          <span className="block text-sm font-medium mb-1">Display name</span>
          <input
            value={displayName}
            onChange={(e) => {
              setDisplayName(e.target.value);
              setSaved(false);
            }}
            maxLength={80}
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <span className="block text-xs text-slate-500 mt-1">
            What other students see. Up to 80 characters.
          </span>
        </label>

        {isPlaceholderEmail ? (
          <p className="text-xs text-slate-500">
            We don't have your real email yet — it comes from your Google account via Clerk
            once a teammate configures the session-token JWT template.
          </p>
        ) : (
          <div className="text-sm text-slate-600">
            <span className="font-medium">Email:</span> {me.email}
            <span className="block text-xs text-slate-500 mt-0.5">
              Synced from your Google account via Clerk. Not editable here.
            </span>
          </div>
        )}

        {saveError && <p className="text-red-600 text-sm">{saveError}</p>}
        {saved && <p className="text-green-700 text-sm">Saved.</p>}

        <button
          type="submit"
          disabled={saving || unchanged || !trimmed}
          className="rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </form>

      <hr />

      <section>
        <h2 className="text-sm font-semibold mb-2">Feedback</h2>
        <p className="text-xs text-slate-500 mb-3">
          Got an idea, found a bug, or just want to send a note? We read everything.
        </p>
        <Link
          to="/feedback"
          className="inline-block rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Submit feedback →
        </Link>
      </section>
    </section>
  );
}
