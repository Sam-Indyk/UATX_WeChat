import { useEffect, useState } from "react";
import { useAuth } from "@clerk/clerk-react";
import { useApi } from "../lib/api";

const POLL_INTERVAL_MS = 30_000;

/**
 * Polls `/api/me/unread-count` every 30s while signed in. Used by the
 * top-nav Inbox badge.
 *
 * Silent on errors — keeps the last known count so a single network blip
 * doesn't make the badge flash empty.
 */
export function useUnreadCount(): number {
  const { isSignedIn } = useAuth();
  const { request } = useApi();
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!isSignedIn) {
      setCount(0);
      return;
    }
    let cancelled = false;
    async function poll() {
      try {
        const data = await request<{ count: number }>("/api/me/unread-count");
        if (!cancelled) setCount(data.count);
      } catch {
        // Silent: keep the previous count rather than flashing 0.
      }
    }
    poll();
    const id = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [isSignedIn, request]);

  return count;
}
