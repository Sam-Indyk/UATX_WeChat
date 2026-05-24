import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiRequest } from "./api";

describe("apiRequest", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("attaches bearer token when provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await apiRequest("/api/me", { token: "abc.def.ghi" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer abc.def.ghi");
  });

  it("throws ApiError with status and body on non-2xx", async () => {
    globalThis.fetch = vi.fn(
      async () => new Response(JSON.stringify({ detail: "nope" }), { status: 403 }),
    ) as unknown as typeof fetch;

    await expect(apiRequest("/api/forbidden")).rejects.toBeInstanceOf(ApiError);
    await expect(apiRequest("/api/forbidden")).rejects.toMatchObject({
      status: 403,
      body: { detail: "nope" },
    });
  });
});
