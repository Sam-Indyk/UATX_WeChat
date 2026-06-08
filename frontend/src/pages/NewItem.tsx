import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApi } from "../lib/api";
import type { Condition, Listing, ListingCategory, PaymentMethod } from "../lib/types";
import { NON_BOOK_CATEGORIES, PAYMENT_METHODS } from "../lib/types";
import { STRIPE_ENABLED } from "../lib/feature-flags";

const CONDITIONS: Condition[] = ["new", "like_new", "good", "fair", "poor"];

/** Create-listing form for the Everything Else marketplace. Distinct from
 *  /listings/new (which is books-only) by design — Sam wants strict
 *  separation: you can only post non-book items from this entrypoint.
 *
 *  Photo is REQUIRED here (unlike the book form where it's optional)
 *  because the Everything Else browse renders the image inline, and a
 *  listing without one is hidden from the browse. We enforce client-side.
 */
export default function NewItem() {
  const nav = useNavigate();
  const { request } = useApi();

  const [category, setCategory] = useState<Exclude<ListingCategory, "book">>("furniture");
  const [title, setTitle] = useState("");
  const [condition, setCondition] = useState<Condition>("good");
  const [priceCents, setPriceCents] = useState(2000);
  const [description, setDescription] = useState("");
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [image, setImage] = useState<File | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function togglePaymentMethod(m: PaymentMethod) {
    setPaymentMethods((prev) =>
      prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m],
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!image) {
      setImageError("A photo is required for marketplace items.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const listing = await request<Listing>("/api/listings", {
        method: "POST",
        body: {
          category,
          // No course_id, no author/edition — backend strips them anyway
          // for non-book categories, but we don't even send them.
          title,
          condition,
          price_cents: priceCents,
          description,
          payment_methods: paymentMethods,
        },
      });

      // Upload the image. If this fails, the listing exists but will be
      // hidden from the Everything Else browse (it filters out
      // image_url IS NULL rows). User can retry from My Listings →
      // Settings tab.
      try {
        const fd = new FormData();
        fd.append("file", image);
        await request<Listing>(`/api/listings/${listing.id}/image`, {
          method: "POST",
          body: fd,
        });
      } catch (e) {
        setError(
          `Listing posted, but the photo upload failed (${String(e)}). ` +
            `You can re-upload from My listings → Settings.`,
        );
      }

      nav(`/listings/${listing.id}`);
    } catch (e) {
      setError(`Couldn't create item: ${String(e)}`);
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4 max-w-lg">
      <header>
        <h1 className="text-2xl font-semibold">List an item</h1>
        <p className="text-sm text-slate-600">
          Posting to <span className="font-medium">Everything else</span> — not a textbook.
          For books, head to the <span className="font-medium">Books</span> tab and
          hit <span className="font-medium">+ Sell a book</span>.
        </p>
      </header>

      <Field label="Category">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as Exclude<ListingCategory, "book">)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          {NON_BOOK_CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </Field>

      <Field label="What is it?">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          maxLength={200}
          placeholder="e.g. Standing desk, IKEA Bekant"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </Field>

      <Field label="Condition">
        <select
          value={condition}
          onChange={(e) => setCondition(e.target.value as Condition)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm capitalize"
        >
          {CONDITIONS.map((c) => (
            <option key={c} value={c}>
              {c.replace("_", " ")}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Price (USD)">
        <input
          type="text"
          inputMode="numeric"
          required
          value={Math.floor(priceCents / 100) || ""}
          onChange={(e) => {
            const digits = e.target.value.replace(/[^0-9]/g, "");
            // Clamp to $100,000 — backend enforces the same cap.
            const dollars = Math.min(parseInt(digits, 10) || 0, 100_000);
            setPriceCents(dollars * 100);
          }}
          placeholder="0"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <span className="block text-xs text-slate-500 mt-1">Whole dollars only, max $100,000.</span>
      </Field>

      <Field label="Description">
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={2000}
          rows={4}
          placeholder="Dimensions, condition details, why you're selling…"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </Field>

      <Field label="Payment methods accepted">
        <p className="text-xs text-slate-600 mb-2">
          {STRIPE_ENABLED ? (
            <>
              Only <span className="font-medium">Stripe</span> is processed in-app —
              buyers can pay through Stripe's hosted checkout and we route the money
              to your connected account. For the others, you'll arrange the transfer
              with the buyer yourself once you've matched in chat.
            </>
          ) : (
            <>You'll arrange the transfer with the buyer yourself once you've matched in chat. (In-app Stripe payments are coming soon.)</>
          )}
        </p>
        <div className="flex flex-col gap-1.5">
          {PAYMENT_METHODS.map((pm) => {
            const disabled = pm.value === "stripe" && !STRIPE_ENABLED;
            return (
              <label
                key={pm.value}
                className={`inline-flex items-center gap-2 text-sm ${
                  disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"
                }`}
              >
                <input
                  type="checkbox"
                  checked={paymentMethods.includes(pm.value) && !disabled}
                  onChange={() => !disabled && togglePaymentMethod(pm.value)}
                  disabled={disabled}
                />
                <span>{pm.label}</span>
                {disabled ? (
                  <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                    Coming soon
                  </span>
                ) : pm.in_app ? (
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-800">
                    Processed in-app
                  </span>
                ) : (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                    Arrange with buyer
                  </span>
                )}
              </label>
            );
          })}
        </div>
        <span className="block text-xs text-slate-500 mt-2">
          Optional. Pick any combination.
        </span>
      </Field>

      <Field label="Photo (required)">
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            setImageError(null);
            if (f && f.size > 5 * 1024 * 1024) {
              setImageError("Image too large (max 5 MB).");
              setImage(null);
              e.target.value = "";
              return;
            }
            setImage(f);
          }}
          className="w-full text-sm"
        />
        {image && (
          <p className="text-xs text-slate-500 mt-1">
            {image.name} ({(image.size / 1024).toFixed(0)} KB)
          </p>
        )}
        {imageError && <p className="text-red-600 text-xs mt-1">{imageError}</p>}
        <span className="block text-xs text-slate-500 mt-1">
          JPEG, PNG, or WebP, up to 5 MB. Listings without a photo are hidden from
          Everything Else.
        </span>
      </Field>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <button
        type="submit"
        disabled={submitting || !image}
        className="rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
      >
        {submitting ? "Posting…" : "Post listing"}
      </button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-sm font-medium mb-1">{label}</span>
      {children}
    </label>
  );
}
