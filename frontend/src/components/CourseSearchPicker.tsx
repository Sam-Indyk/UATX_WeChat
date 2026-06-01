import { useEffect, useMemo, useRef, useState } from "react";
import type { Course } from "../lib/types";

type Props = {
  courses: Course[];
  selectedId: string | null;
  onChange: (id: string | null) => void;
  placeholder?: string;
  /** Show an explicit "deselect" option at the top of the dropdown. */
  allowEmpty?: boolean;
  emptyLabel?: string;
};

/** Single-select combobox for picking a course out of the (~167-course)
 *  catalog. Replaces the scroll-through-everything <select> on the
 *  NewListing form and the Listings page filter.
 *
 *  Behaviors:
 *  - Selected course's "CODE — Title" shows in the input.
 *  - Typing filters by code prefix OR title substring.
 *  - Dropdown opens on focus, closes on selection / click-outside / Esc.
 *  - onMouseDown on options (not onClick) so the input doesn't blur
 *    before the click registers, which causes flicker.
 */
export default function CourseSearchPicker({
  courses,
  selectedId,
  onChange,
  placeholder = "Search courses…",
  allowEmpty = false,
  emptyLabel = "(none)",
}: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // When the parent's selectedId changes (or courses list arrives), sync
  // the input's display text to match. Don't clobber an in-progress search.
  useEffect(() => {
    if (open) return;
    const c = courses.find((c) => c.id === selectedId);
    setQuery(c ? `${c.code} — ${c.title}` : "");
  }, [selectedId, courses, open]);

  // Close on click outside.
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return courses;
    return courses.filter(
      (c) => c.code.toLowerCase().includes(q) || c.title.toLowerCase().includes(q),
    );
  }, [query, courses]);

  function pick(id: string | null) {
    onChange(id);
    setOpen(false);
    // Re-sync the input display on the next tick (useEffect dep).
  }

  return (
    <div ref={wrapperRef} className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setOpen(false);
            (e.target as HTMLInputElement).blur();
          }
        }}
        placeholder={placeholder}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      {open && (
        <ul className="absolute z-20 mt-1 w-full max-h-72 overflow-y-auto rounded-md border border-slate-300 bg-white shadow-lg">
          {allowEmpty && (
            <li>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(null);
                }}
                className="block w-full text-left px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
              >
                {emptyLabel}
              </button>
            </li>
          )}
          {filtered.length === 0 && (
            <li className="px-3 py-2 text-sm text-slate-500">No matches</li>
          )}
          {filtered.slice(0, 100).map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(c.id);
                }}
                className={`block w-full text-left px-3 py-2 text-sm hover:bg-slate-100 ${
                  c.id === selectedId ? "bg-slate-50" : ""
                }`}
              >
                <span className="font-medium">{c.code}</span>
                <span className="text-slate-600 ml-2">{c.title}</span>
              </button>
            </li>
          ))}
          {filtered.length > 100 && (
            <li className="px-3 py-2 text-xs text-slate-500">
              Showing first 100 of {filtered.length}. Type to narrow further.
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
