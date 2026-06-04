/** Human-friendly relative timestamp.
 *
 *  - <1 min  → "just now"
 *  - <1 hr   → "12 min ago"
 *  - <1 day  → "3 hr ago"
 *  - <30 day → "5 days ago"
 *  - else    → "Mar 14" (or "Mar 14, 2024" if it's a previous year)
 *
 *  Used on listing cards across Books browse, Everything Else, My
 *  Listings, and user profiles — a small freshness signal that
 *  doesn't dominate the card.
 */
export function formatRelativeDate(iso: string): string {
  const then = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - then.getTime();
  const diffSec = Math.max(0, Math.floor(diffMs / 1000));
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  if (diffHr < 24) return `${diffHr} hr ago`;
  if (diffDay < 30) return `${diffDay} day${diffDay === 1 ? "" : "s"} ago`;

  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  if (then.getFullYear() !== now.getFullYear()) opts.year = "numeric";
  return then.toLocaleDateString(undefined, opts);
}
