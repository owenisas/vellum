import type { ProofBundleV2 } from "../api/types";

export function useProofBundle(bundle: ProofBundleV2 | undefined | null) {
  if (!bundle) return { explorerUrl: null, chainType: null, isValid: false };
  const anchor = bundle.anchors[0];
  let explorerUrl: string | null = bundle.verification_hints.explorer_url || null;
  if (anchor?.type === "solana_per_response" || anchor?.type === "solana_merkle") {
    if (anchor.tx_hash && !explorerUrl) {
      explorerUrl = `https://explorer.solana.com/tx/${anchor.tx_hash}?cluster=devnet`;
    }
  }
  return {
    explorerUrl,
    chainType: bundle.verification_hints.chain_type,
    isValid: bundle.watermark.detected || bundle.watermark.valid_count > 0,
    bundleId: bundle.bundle_id,
    inclusionProof: anchor?.inclusion_proof || null,
    merkleRoot: anchor?.merkle_root || null,
  };
}
