import {
  ReactNode,
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useAuth } from "@clerk/clerk-react";
import { useApi } from "../lib/api";

const POLL_INTERVAL_MS = 30_000;

/** Per-context unread breakdown. Mirrors the backend's UnreadCountsOut.
 *
 *  - listings:  conversations on listings I posted (I'm the seller)
 *  - inquiries: conversations on listings I'm interested in (I'm the buyer)
 *  - dms:       direct-message conversations (no listing)
 *  - total:     sum of the above (kept on the wire so consumers that just
 *               want a single number don't have to add).
 */
export type UnreadCounts = {
  listings: number;
  inquiries: number;
  dms: number;
  total: number;
};

type UnreadContextValue = {
  counts: UnreadCounts;
  /** Force an immediate refetch. The Conversation page calls this after
   *  mark-read so the nav badge clears without waiting for the next poll. */
  refetch: () => void;
};

const EMPTY_COUNTS: UnreadCounts = { listings: 0, inquiries: 0, dms: 0, total: 0 };

const UnreadContext = createContext<UnreadContextValue>({
  counts: EMPTY_COUNTS,
  refetch: () => {},
});

export function UnreadProvider({ children }: { children: ReactNode }) {
  const { isSignedIn } = useAuth();
  const { request } = useApi();
  const [counts, setCounts] = useState<UnreadCounts>(EMPTY_COUNTS);

  const refetch = useCallback(async () => {
    if (!isSignedIn) {
      setCounts(EMPTY_COUNTS);
      return;
    }
    try {
      const data = await request<UnreadCounts>("/api/me/unread-counts");
      setCounts(data);
    } catch {
      // Silent — keep the previous counts rather than flashing 0 on a blip.
    }
  }, [isSignedIn, request]);

  useEffect(() => {
    if (!isSignedIn) {
      setCounts(EMPTY_COUNTS);
      return;
    }
    refetch();
    const id = setInterval(refetch, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isSignedIn, refetch]);

  // Using createElement instead of JSX so this file can stay .ts.
  return createElement(
    UnreadContext.Provider,
    { value: { counts, refetch } },
    children,
  );
}

export function useUnread() {
  return useContext(UnreadContext);
}
