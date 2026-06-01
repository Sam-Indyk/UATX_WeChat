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

type UnreadContextValue = {
  count: number;
  /** Force an immediate refetch. The Conversation page calls this after
   *  mark-read so the nav badge clears without waiting for the next poll. */
  refetch: () => void;
};

const UnreadContext = createContext<UnreadContextValue>({
  count: 0,
  refetch: () => {},
});

export function UnreadProvider({ children }: { children: ReactNode }) {
  const { isSignedIn } = useAuth();
  const { request } = useApi();
  const [count, setCount] = useState(0);

  const refetch = useCallback(async () => {
    if (!isSignedIn) {
      setCount(0);
      return;
    }
    try {
      const data = await request<{ count: number }>("/api/me/unread-count");
      setCount(data.count);
    } catch {
      // Silent — keep the previous count rather than flashing 0 on a blip.
    }
  }, [isSignedIn, request]);

  useEffect(() => {
    if (!isSignedIn) {
      setCount(0);
      return;
    }
    refetch();
    const id = setInterval(refetch, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isSignedIn, refetch]);

  // Using createElement instead of JSX so this file can stay .ts.
  return createElement(
    UnreadContext.Provider,
    { value: { count, refetch } },
    children,
  );
}

export function useUnread() {
  return useContext(UnreadContext);
}
