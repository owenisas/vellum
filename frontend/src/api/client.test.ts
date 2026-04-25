import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, get, post, setTokenGetter } from "./client";

const FETCH = global.fetch;

describe("api client", () => {
  beforeEach(() => {
    setTokenGetter(null);
  });

  afterEach(() => {
    global.fetch = FETCH;
    vi.restoreAllMocks();
  });

  it("attaches Authorization header when token getter is set", async () => {
    setTokenGetter(async () => "abc.def");
    let captured: Headers | null = null;
    global.fetch = vi.fn(async (_url, init: RequestInit) => {
      captured = init.headers as Headers;
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch;

    await get("/api/health");
    expect(captured).toBeTruthy();
    const headers = captured as unknown as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer abc.def");
  });

  it("throws ApiError on non-2xx response", async () => {
    global.fetch = vi.fn(async () => {
      return new Response(JSON.stringify({ detail: "nope", error_id: "deadbeef" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch;

    await expect(post("/api/anchor", { x: 1 })).rejects.toBeInstanceOf(ApiError);
  });

  it("retries on 5xx and gives up", async () => {
    let calls = 0;
    global.fetch = vi.fn(async () => {
      calls += 1;
      return new Response(JSON.stringify({ error: "boom" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch;

    await expect(get("/api/health", { retries: 2 })).rejects.toBeTruthy();
    expect(calls).toBe(3);
  });
});
