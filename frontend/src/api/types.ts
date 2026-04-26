export interface ChatRequest {
  prompt: string;
  model?: string;
  provider?: string;
  watermark?: boolean;
  watermark_params?: WatermarkParams;
}

export interface WatermarkParams {
  issuer_id: number;
  model_id: number;
  model_version_id: number;
  key_id?: number;
  repeat_interval_tokens?: number;
}

export interface ChatResponse {
  text: string;
  raw_text: string;
  thinking: string;
  watermarked: boolean;
  model: string;
  provider: string;
  usage: { input_tokens: number; output_tokens: number };
  error?: string;
}

export interface AnchorRequest {
  text: string;
  raw_text?: string;
  issuer_id: number;
  signature_hex: string;
  sig_scheme: "eip712" | "eip191_personal_sign";
  timestamp: number;
  bundle_nonce_hex?: string;
  metadata?: Record<string, unknown>;
}

export interface ChainReceipt {
  tx_hash: string;
  block_num: number;
  data_hash: string;
  issuer_id: number;
  timestamp: string;
  solana_tx_signature?: string;
  merkle_root?: string;
  leaf_index?: number;
  inclusion_proof?: { hash: string; side: "L" | "R" }[];
}

export interface AnchorResponse {
  verified_signer: string;
  eth_address: string;
  sha256_hash: string;
  chain_receipt: ChainReceipt;
  proof_bundle_v2: ProofBundleV2;
  bundle_status: "ok" | "pending_batch";
}

export interface ProofBundleV2 {
  spec: "veritext-proof-bundle/v2";
  bundle_id: string;
  signed_fields: string[];
  hashing: { algorithm: "sha256"; text_hash: string; input_encoding: "utf-8"; normalization: "none" };
  issuer: {
    issuer_id: number;
    name: string;
    eth_address: string;
    public_key_hex: string;
    current_key_id: number;
    key_history: unknown[];
  };
  signature: {
    scheme: "eip712" | "eip191_personal_sign";
    canonicalization: "rfc8785";
    signed_payload: string;
    signature_hex: string;
    recoverable_address: boolean;
    typed_data?: unknown;
  };
  watermark: {
    detected: boolean;
    injection_mode: "whitespace" | "grapheme";
    generation_time?: { type: string; present: boolean; detector_score: number; p_value: number } | null;
    tag_count: number;
    valid_count: number;
    invalid_count: number;
    payloads: WatermarkPayloadInfo[];
  };
  encrypted_payload_metadata?: { key_kid: number; algorithm: "aes-128-ccm" } | null;
  anchors: AnchorInfo[];
  verification_hints: { chain_type: string; rpc_url?: string; explorer_url?: string; merkle_root?: string };
}

export interface WatermarkPayloadInfo {
  schema_version: number;
  issuer_id: number;
  model_id: number;
  model_version_id: number;
  key_id: number;
  fec: { type: string; errors_corrected: number; code_valid: boolean };
  encrypted: boolean;
  nonce_hex?: string;
  raw_payload_hex: string;
}

export interface AnchorInfo {
  type: "solana_per_response" | "solana_merkle" | "simulated_chain";
  tx_hash?: string;
  block_num?: number;
  timestamp: string;
  memo_encoding?: "borsh" | "json";
  memo_borsh_hex?: string;
  merkle_root?: string;
  inclusion_proof?: { hash: string; side: "L" | "R" }[];
  leaf_index?: number;
}

export interface VerifyResponse {
  verified: boolean;
  sha256_hash: string;
  issuer_id?: number;
  company?: string;
  eth_address?: string;
  block_num?: number;
  tx_hash?: string;
  timestamp?: string;
  watermark: { present: boolean; unicode: { detected: boolean; tag_count: number }; statistical: unknown };
  proof_bundle_v2?: ProofBundleV2;
  reason?: string;
}
