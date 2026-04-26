import { env } from "../config/env";

export class ApiError extends Error {
  status: number;
  detail: string;
  errorId?: string;
  constructor(status: number, detail: string, errorId?: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.errorId = errorId;
  }
}

let _tokenGetter: (() => Promise<string | null>) | null = null;

export function setTokenGetter(fn: () => Promise<string | null>): void {
  _tokenGetter = fn;
}

export interface RequestOptions {
  timeout?: number;
  retries?: number;
}

export async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts: RequestOptions = {},
): Promise<T> {
  const { timeout = 30_000, retries = 1 } = opts;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (_tokenGetter) {
    const tok = await _tokenGetter();
    if (tok) headers["Authorization"] = `Bearer ${tok}`;
  }

  let lastErr: unknown = null;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeout);
    try {
      const resp = await fetch(env.API_BASE_URL + path, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: ctrl.signal,
      });
      clearTimeout(t);
      if (!resp.ok) {
        const txt = await resp.text();
        let detail = txt;
        let errorId: string | undefined;
        try {
          const j = JSON.parse(txt);
          detail = j.detail || j.error || txt;
          errorId = j.error_id;
        } catch {}
        throw new ApiError(resp.status, detail, errorId);
      }
      return (await resp.json()) as T;
    } catch (err) {
      clearTimeout(t);
      lastErr = err;
      if (err instanceof ApiError && err.status < 500) throw err;
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
        continue;
      }
    }
  }
  throw lastErr;
}

export const get = <T>(path: string, opts?: RequestOptions) => request<T>("GET", path, undefined, opts);
export const post = <T>(path: string, body: unknown, opts?: RequestOptions) =>
  request<T>("POST", path, body, opts);
