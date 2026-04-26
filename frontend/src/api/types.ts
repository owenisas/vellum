/** Shared API response types — keep in sync with src/vellum/models. */

export interface HealthResponse {
  status: string;
  demo_mode: "live" | "fixture";
  chain_backend: "simulated" | "solana";
  solana_cluster: string | null;
  auth0_enabled: boolean;
  google_api_key_configured: boolean;
  minimax_api_key_configured: boolean;
  chain: { length: number; valid: boolean; message: string };
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
}

export interface ModelsResponse {
  google: ModelInfo[];
  minimax: ModelInfo[];
  bedrock: ModelInfo[];
}

export interface WmParams {
  schema_version?: number;
  issuer_id?: number;
  model_id?: number;
  model_version_id?: number;
  key_id?: number;
  repeat_interval_tokens?: number;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system" | "model";
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  provider?: string;
  model?: string;
  system?: string;
  max_tokens?: number;
  temperature?: number;
  watermark?: boolean;
  wm_params?: WmParams;
}

export interface ChatResponse {
  text: string;
  raw_text: string;
  thinking: string;
  raw_thinking: string;
  watermarked: boolean;
  model: string;
  provider: string;
  usage: { input_tokens: number; output_tokens: number };
  error?: string;
}

export interface WatermarkPayload {
  schema_version: number;
  issuer_id: number;
  model_id: number;
  model_version_id: number;
  key_id: number;
  crc_valid: boolean;
  raw_payload_hex: string;
}

export interface WatermarkInfo {
  watermarked: boolean;
  tag_count: number;
  valid_count: number;
  invalid_count: number;
  payloads: WatermarkPayload[];
}

export interface DetectResponse {
  text: string;
  watermark: WatermarkInfo;
}

export interface ApplyResponse {
  text: string;
  watermarked: string;
  payload_hex: string;
}

export interface StripResponse {
  text: string;
  stripped: string;
  removed: number;
}

export interface CompanyResponse {
  id: number;
  name: string;
  issuer_id: number;
  eth_address: string;
  public_key_hex: string;
  active: boolean;
  created_at: string | null;
}

export interface CreateCompanyResponse extends CompanyResponse {
  private_key_hex: string | null;
  note: string | null;
}

export interface ChainBlock {
  block_num: number;
  prev_hash: string;
  tx_hash: string;
  data_hash: string;
  issuer_id: number;
  signature_hex: string;
  timestamp: string;
  solana_tx_signature: string | null;
}

export interface ChainStatus {
  length: number;
  valid: boolean;
  message: string;
  backend: string;
  latest_block_num: number | null;
  latest_data_hash: string | null;
}

export interface ChainReceipt {
  tx_hash: string;
  block_num: number;
  data_hash: string;
  issuer_id: number;
  timestamp: string;
  solana_tx_signature: string | null;
}

export interface ProofBundleV2 {
  spec: string;
  bundle_id: string;
  hashing: Record<string, unknown>;
  issuer: Record<string, unknown>;
  agent_action?: Record<string, unknown> | null;
  wallet_proofs?: Array<Record<string, unknown>>;
  signature: Record<string, unknown>;
  watermark: Record<string, unknown>;
  anchors: Array<Record<string, unknown>>;
  verification_hints: Record<string, unknown>;
}

export interface WalletProof {
  wallet_type: "evm" | "solana";
  address: string;
  message: string;
  signature: string;
  signature_encoding?: "base64" | "hex" | "base58";
  chain_id?: string | null;
  cluster?: string | null;
  tx_signature?: string | null;
}

export interface AnchorResponse {
  verified_signer: string;
  eth_address: string;
  sha256_hash: string;
  chain_receipt: ChainReceipt;
  proof_bundle_v2: ProofBundleV2;
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

export interface DemoScenarioResponse {
  company: {
    name: string;
    private_key_hex: string;
    public_key_hex: string;
    eth_address: string;
  };
  text: string;
  watermarked_text: string;
  watermark: WatermarkInfo;
  signature_hex: string;
  sha256_hash: string;
  instructions: string[];
}

export interface SolanaBalanceResponse {
  address: string;
  cluster: string;
  balance_sol: number;
  balance_lamports: number;
}

export interface SolanaVerifyResponse {
  verified: boolean;
  tx_signature: string;
  slot: number | null;
  memo_data: Record<string, unknown> | null;
  explorer_url: string | null;
  reason: string | null;
}

export interface ApiErrorBody {
  detail?: string;
  error?: string;
  error_id?: string;
}
