import { FormEvent, useEffect, useState } from "react";
import { apiRequest, useApi } from "../lib/api";
import type { Condition, Course, Listing, ListingStatus } from "../lib/types";
import CourseSearchPicker from "./CourseSearchPicker";

const CONDITIONS: Condition[] = ["new", "like_new", "good", "fair", "poor"];

type Props = {
  listing: Listing;
  /** Called after a successful save so the parent can refetch and show
   *  the new values everywhere they appear (header, image, etc.). */
  onChange: () => void;
};

export default function ListingSettingsForm({ listing, onChange }: Props) {
  const { request } = useApi();

  const [title_, setTitle_] = useState(listing.title);
  const [author_, setAuthor_] = useState(listing.author ?? "");
  const [edition_, setEdition_] = useState(listing.edition ?? "");
  const [condition, setCondition] = useState<Condition>(listing.condition);
  const [priceCents, setPriceCents] = useState(listing.price_cents);
  const [description, setDescription] = useState(listing.description);
  const [courseId, setCourseId] = useState<string | null>(listing.course?.id ?? null);

  const [courses, setCourses] = useState<Course[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageUploading, setImageUploading] = useState(false);

  useEffect(() => {
    apiRequest<Course[]>("/api/courses").then(setCourses).catch(() => {});
  }, []);

  // When the parent refetches and re-mounts us with a different listing,
  // sync the local form state.
  useEffect(() => {
    setTitle_(listing.title);
    setAuthor_(listing.author ?? "");
    setEdition_(listing.edition ?? "");
    setCondition(listing.condition);
    setPriceCents(listing.price_cents);
    setDescription(listing.description);
    setCourseId(listing.course?.id ?? null);
  }, [listing]);

  async function save(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await request<Listing>(`/api/listings/${listing.id}`, {
        method: "PATCH",
        body: {
          title: title_,
          author: author_,
          edition: edition_ || null,
          condition,
          price_cents: priceCents,
          description,
          course_id: courseId,
        },
      });
      setSavedAt(Date.now());
      onChange();
    } catch (e) {
      setError(`Couldn't save: ${String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(status: ListingStatus) {
    setError(null);
    try {
      await request<Listing>(`/api/listings/${listing.id}`, {
        method: "PATCH",
        body: { status },
      });
      onChange();
    } catch (e) {
      setError(`Couldn't update status: ${String(e)}`);
    }
  }

  async function uploadImage(e: FormEvent) {
    e.preventDefault();
    if (!imageFile) return;
    setImageUploading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", imageFile);
      await request<Listing>(`/api/listings/${listing.id}/image`, {
        method: "POST",
        body: fd,
      });
      setImageFile(null);
      onChange();
    } catch (e) {
      setError(`Couldn't upload image: ${String(e)}`);
    } finally {
      setImageUploading(false);
    }
  }

  return (
    <div className="space-y-6 max-w-lg">
      {/* Status / take-down */}
      <section>
        <h2 className="text-sm font-semibold mb-2">Status</h2>
        <p className="text-xs text-slate-500 mb-2">
          Current status: <span className="font-medium capitalize">{listing.status}</span>
        </p>
        <div className="flex flex-wrap gap-2">
          {(["active", "reserved", "sold", "withdrawn"] as ListingStatus[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => changeStatus(s)}
              disabled={listing.status === s}
              className={`rounded-md border px-3 py-1.5 text-xs ${
                listing.status === s
                  ? "border-slate-400 bg-slate-100 text-slate-700"
                  : "border-slate-300 hover:bg-slate-50"
              }`}
            >
              {s === "withdrawn" ? "Take down" : `Mark ${s}`}
            </button>
          ))}
        </div>
      </section>

      <hr />

      {/* Image */}
      <section>
        <h2 className="text-sm font-semibold mb-2">Photo</h2>
        {listing.image_url && (
          <img
            src={listing.image_url}
            alt=""
            className="mb-3 max-h-48 rounded-md border border-slate-200 object-contain"
          />
        )}
        <form onSubmit={uploadImage} className="flex items-center gap-2">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
            className="text-sm"
          />
          <button
            type="submit"
            disabled={!imageFile || imageUploading}
            className="rounded-md bg-slate-900 px-3 py-1.5 text-white text-xs font-medium hover:bg-slate-800 disabled:opacity-50"
          >
            {imageUploading ? "Uploading…" : "Upload"}
          </button>
        </form>
      </section>

      <hr />

      {/* Edit form */}
      <form onSubmit={save} className="space-y-3">
        <h2 className="text-sm font-semibold">Listing details</h2>

        <Field label="Title">
          <input
            value={title_}
            onChange={(e) => setTitle_(e.target.value)}
            required
            maxLength={200}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </Field>

        <Field label="Author">
          <input
            value={author_}
            onChange={(e) => setAuthor_(e.target.value)}
            required
            maxLength={200}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </Field>

        <Field label="Edition (optional)">
          <input
            value={edition_}
            onChange={(e) => setEdition_(e.target.value)}
            maxLength={40}
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
            type="number"
            min={0}
            step="0.01"
            value={(priceCents / 100).toFixed(2)}
            onChange={(e) => setPriceCents(Math.round(parseFloat(e.target.value || "0") * 100))}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </Field>

        <Field label="Course">
          <CourseSearchPicker
            courses={courses ?? []}
            selectedId={courseId}
            onChange={setCourseId}
            placeholder="Search for a course…"
          />
          <p className="mt-1 text-xs text-slate-500">
            Currently: {listing.course ? `${listing.course.code} — ${listing.course.title}` : "no course"}
          </p>
        </Field>

        <Field label="Description">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            maxLength={2000}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </Field>

        {error && <p className="text-red-600 text-sm">{error}</p>}
        {savedAt && Date.now() - savedAt < 4000 && (
          <p className="text-green-700 text-sm">Saved.</p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-slate-900 px-4 py-2 text-white text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save changes"}
        </button>
      </form>
    </div>
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
