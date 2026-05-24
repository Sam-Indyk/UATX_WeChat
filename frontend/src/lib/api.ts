/**
 * Tiny API client. Attaches the Clerk JWT automatically.
 *
 * Use `useApi()` from a React component to get a `request` function that
 * carries the current Clerk session token; for non-React callers pass the
 * token in explicitly.
 */
import { useAuth } from "@clerk/clerk-react";
import { useCallback } from "react";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(`API ${status}`);
    this.status = status;
    this.body = body;
  }
}

export type ApiRequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string | null;
};

export async function apiRequest<T>(
  path: string,
  { method = "GET", body, token }: ApiRequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const text = await res.text();
  const parsed: unknown = text ? safeJson(text) : null;

  if (!res.ok) throw new ApiError(res.status, parsed);
  return parsed as T;
}

function safeJson(s: string): unknown {
  try {
    return JSON.parse(s);
  } catch {
    return s;
  }
}

export function useApi() {
  const { getToken } = useAuth();

  const request = useCallback(
    async <T>(path: string, opts: Omit<ApiRequestOptions, "token"> = {}): Promise<T> => {
      const token = await getToken();
      return apiRequest<T>(path, { ...opts, token });
    },
    [getToken],
  );

  return { request };
}
