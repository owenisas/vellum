export const DEFAULT_API_BASE_URL = "https://vellum-387oq.ondigitalocean.app";

export const KNOWN_API_BASE_URLS = [
  DEFAULT_API_BASE_URL,
  "https://vellum-auth0-ttohk.ondigitalocean.app",
] as const;

export interface WatermarkInfo {
  watermarked: boolean;
  tag_count: number;
  valid_count: number;
  invalid_count: number;
  payloads: Array<Record<string, unknown>>;
}

export interface ProofBundleV2 {
  spec: string;
  bundle_id: string;
  hashing: Record<string, unknown>;
  issuer: Record<string, unknown>;
  agent_action?: Record<string, unknown> | null;
  wallet_proofs: Array<Record<string, unknown>>;
  signature: Record<string, unknown>;
  watermark: Record<string, unknown>;
  anchors: Array<Record<string, unknown>>;
  verification_hints: Record<string, unknown>;
}

export interface VerifyResponse {
  verified: boolean;
  sha256_hash: string;
  issuer_id: number | null;
  company: string | null;
  eth_address: string | null;
  block_num: number | null;
  tx_hash: string | null;
  timestamp: string | null;
  watermark: WatermarkInfo;
  proof_bundle_v2: ProofBundleV2 | null;
  reason: string | null;
}

export interface VerifyResult {
  ok: boolean;
  apiBaseUrl: string;
  checkedAt: number;
  response?: VerifyResponse;
  error?: string;
}

export const normalizeApiBaseUrl = (value: string | undefined): string => {
  const raw = (value ?? DEFAULT_API_BASE_URL).trim().replace(/\/+$/, "");
  if (!raw) return DEFAULT_API_BASE_URL;
  if (!/^https?:\/\//i.test(raw)) return `https://${raw}`;
  return raw;
};

export const verifyText = async (
  text: string,
  apiBaseUrl: string,
): Promise<VerifyResult> => {
  const base = normalizeApiBaseUrl(apiBaseUrl);
  const checkedAt = Date.now();

  try {
    const resp = await fetch(`${base}/api/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!resp.ok) {
      let detail = `${resp.status} ${resp.statusText}`.trim();
      try {
        const body = (await resp.json()) as { detail?: unknown };
        if (typeof body.detail === "string") detail = body.detail;
      } catch {
        /* non-JSON error body */
      }
      return {
        ok: false,
        apiBaseUrl: base,
        checkedAt,
        error: `Verifier request failed: ${detail}`,
      };
    }

    const response = (await resp.json()) as VerifyResponse;
    return { ok: true, apiBaseUrl: base, checkedAt, response };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      apiBaseUrl: base,
      checkedAt,
      error: `Could not reach verifier: ${message}`,
    };
  }
};
