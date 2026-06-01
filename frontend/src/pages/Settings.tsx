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

  if (loadError) return <p className="text-red-600">{loadError}</p>;
  if (!me) return <p className="text-slate-500">Loading…</p>;

  const trimmed = displayName.trim();
  const unchanged = trimmed === me.display_name;

  return (
    <section className="space-y-6 max-w-md">
      <header>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-slate-600">
          How you appear to other students in chats, listings, and the classmates view.
        </p>
      </header>

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

        <div className="text-sm text-slate-600">
          <span className="font-medium">Email:</span> {me.email}
          <span className="block text-xs text-slate-500 mt-0.5">
            Synced from your Google account via Clerk. Not editable here.
          </span>
        </div>

        {saveError && <p className="text-red-600 text-sm">{saveError}</p>}
        {saved && <p className="text-green-700 text-sm">Saved.</p>}

        <button
          type="submit"
          disabled={saving || unchanged || !trimmed}
          className="rounded-md bg-slate-900 px-4 py-2 text-white text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </form>
    </section>
  );
}
