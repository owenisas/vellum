import env from "../config/env";
import type { ApiErrorBody } from "./types";

type TokenGetter = () => Promise<string>;

let tokenGetter: TokenGetter | null = null;

export function setTokenGetter(fn: TokenGetter | null): void {
  tokenGetter = fn;
}

async function authHeaders(): Promise<Record<string, string>> {
  if (!tokenGetter) return {};
  try {
    const token = await tokenGetter();
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

export class ApiError extends Error {
  status: number;
  errorId?: string;

  constructor(status: number, message: string, errorId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorId = errorId;
  }
}

export interface RequestOptions {
  timeout?: number;
  retries?: number;
  signal?: AbortSignal;
}

const DEFAULT_TIMEOUT = 30_000;
const DEFAULT_RETRIES = 1;

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(await authHeaders()),
  };

  const url = `${env.API_BASE_URL}${path}`;
  const retries = options.retries ?? DEFAULT_RETRIES;

  let lastError: unknown = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const t = setTimeout(
      () => controller.abort(),
      options.timeout ?? DEFAULT_TIMEOUT,
    );

    // Forward an externally provided AbortSignal too.
    const onAbort = () => controller.abort();
    options.signal?.addEventListener("abort", onAbort);

    try {
      const resp = await fetch(url, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      clearTimeout(t);
      options.signal?.removeEventListener("abort", onAbort);

      if (!resp.ok) {
        const errBody = (await resp.json().catch(() => ({}))) as ApiErrorBody;
        throw new ApiError(
          resp.status,
          errBody.detail ?? errBody.error ?? resp.statusText,
          errBody.error_id,
        );
      }
      // 204 No Content
      if (resp.status === 204) return undefined as T;
      return (await resp.json()) as T;
    } catch (err) {
      clearTimeout(t);
      options.signal?.removeEventListener("abort", onAbort);
      lastError = err;

      // Don't retry on 4xx errors
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
        throw err;
      }
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
      }
    }
  }
  throw lastError instanceof Error
    ? lastError
    : new Error("Request failed");
}

export const get = <T>(path: string, opts?: RequestOptions) =>
  request<T>("GET", path, undefined, opts);
export const post = <T>(path: string, body: unknown, opts?: RequestOptions) =>
  request<T>("POST", path, body, opts);
export const put = <T>(path: string, body: unknown, opts?: RequestOptions) =>
  request<T>("PUT", path, body, opts);
export const del = <T>(path: string, opts?: RequestOptions) =>
  request<T>("DELETE", path, undefined, opts);
