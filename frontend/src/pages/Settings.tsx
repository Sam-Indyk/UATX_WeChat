import { FormEvent, useEffect, useState } from "react";
import { useApi } from "../lib/api";
import type { User } from "../lib/types";

export default function Settings() {
  const { request } = useApi();

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
    </section>
  );
}
