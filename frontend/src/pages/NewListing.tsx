import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest, useApi } from "../lib/api";
import CourseSearchPicker from "../components/CourseSearchPicker";
import type { Course, Listing, PaymentMethod } from "../lib/types";
import { PAYMENT_METHODS } from "../lib/types";

const CONDITIONS = ["new", "like_new", "good", "fair", "poor"] as const;

export default function NewListing() {
  const nav = useNavigate();
  const { request } = useApi();

  const [courses, setCourses] = useState<Course[] | null>(null);
  const [coursesError, setCoursesError] = useState<string | null>(null);

  const [courseId, setCourseId] = useState("");
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [edition, setEdition] = useState("");
  const [condition, setCondition] = useState<typeof CONDITIONS[number]>("good");
  const [priceCents, setPriceCents] = useState(1500);
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

  useEffect(() => {
    apiRequest<Course[]>("/api/courses").then(setCourses).catch((e) =>
      setCoursesError(`Couldn't load courses: ${String(e)}`),
    );
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const listing = await request<Listing>("/api/listings", {
        method: "POST",
        body: {
          category: "book",
          course_id: courseId || null,
          title: title,
          author: author,
          edition: edition || null,
          condition,
          price_cents: priceCents,
          description,
          payment_methods: paymentMethods,
        },
      });
      // If the user picked an image, upload it now. Failure here is
      // non-fatal: the listing is already created, we just couldn't
      // attach the photo. Surface the error but still navigate.
      if (image) {
        try {
          const fd = new FormData();
          fd.append("file", image);
          await request<Listing>(`/api/listings/${listing.id}/image`, {
            method: "POST",
            body: fd,
          });
        } catch (e) {
          setError(`Listing posted, but the image upload failed: ${String(e)}`);
        }
      }
      nav(`/listings/${listing.id}`);
    } catch (e) {
      setError(`Couldn't create listing: ${String(e)}`);
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4 max-w-lg">
      <h1 className="text-2xl font-semibold">Sell a book</h1>

      <Field label="Course (optional)">
        {coursesError && <p className="text-red-600 text-sm">{coursesError}</p>}
        <CourseSearchPicker
          courses={courses ?? []}
          selectedId={courseId || null}
          onChange={(id) => setCourseId(id ?? "")}
          placeholder="Search for a course…"
          allowEmpty
          emptyLabel="— no course (general item) —"
        />
      </Field>

      <Field label="Book title">
        <input
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          maxLength={200}
        />
      </Field>

      <Field label="Author (optional)">
        <input
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          maxLength={200}
        />
      </Field>

      <Field label="Edition (optional)">
        <input
          value={edition}
          onChange={(e) => setEdition(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          maxLength={40}
        />
      </Field>

      <Field label="Condition">
        <select
          value={condition}
          onChange={(e) => setCondition(e.target.value as typeof CONDITIONS[number])}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm capitalize"
        >
          {CONDITIONS.map((c) => (
            <option key={c} value={c} className="capitalize">{c.replace("_", " ")}</option>
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
            // Clamp to $100,000 — backend enforces the same cap. Without
            // this the user could type "1111111111" and overflow Postgres
            // INT4, getting a 500 instead of a clean form error.
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
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </Field>

      <Field label="Payment methods accepted">
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          {PAYMENT_METHODS.map((pm) => (
            <label
              key={pm.value}
              className="inline-flex items-center gap-1.5 text-sm cursor-pointer"
            >
              <input
                type="checkbox"
                checked={paymentMethods.includes(pm.value)}
                onChange={() => togglePaymentMethod(pm.value)}
              />
              {pm.label}
            </label>
          ))}
        </div>
        <span className="block text-xs text-slate-500 mt-1">
          Optional. Pick any combination — buyers will see which methods you accept.
        </span>
      </Field>

      <Field label="Photo (optional)">
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
          JPEG, PNG, or WebP, up to 5 MB.
        </span>
      </Field>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
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
