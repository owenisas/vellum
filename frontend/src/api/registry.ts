import { get, post } from "./client";
import type {
  AnchorResponse,
  HealthResponse,
  ProofBundleV2,
  VerifyResponse,
  WmParams,
} from "./types";
import { useMutation, useQuery } from "@tanstack/react-query";

export const registryApi = {
  health: () => get<HealthResponse>("/api/health"),
  anchor: (req: {
    text: string;
    raw_text?: string;
    signature_hex: string;
    issuer_id: number;
    metadata?: Record<string, unknown>;
    wm_params?: WmParams;
  }) => post<AnchorResponse>("/api/anchor", req),
  verify: (text: string) => post<VerifyResponse>("/api/verify", { text }),
  proofByText: (text: string) =>
    post<{ found: boolean; proof_bundle_v2: ProofBundleV2 | null; reason: string | null }>(
      "/api/proof/text",
      { text },
    ),
  proofByTx: (tx_hash: string) =>
    get<{ found: boolean; proof_bundle_v2: ProofBundleV2 | null; reason: string | null }>(
      `/api/proof/tx/${encodeURIComponent(tx_hash)}`,
    ),
  proofSpec: () => get<{ spec: string; description: string; sections: string[] }>(
    "/api/proof/spec",
  ),
};

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: registryApi.health,
    refetchInterval: 30_000,
  });
}

export function useAnchor() {
  return useMutation({ mutationFn: registryApi.anchor });
}

export function useVerify() {
  return useMutation({ mutationFn: registryApi.verify });
}
