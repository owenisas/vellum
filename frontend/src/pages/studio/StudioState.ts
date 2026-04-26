import type { AnchorResponse, VerifyResponse, WalletProof } from "../../api/types";

export type Stage = "write" | "sign" | "anchor" | "prove";
export type SignerMode = "local" | "metamask";

export const STAGES: { id: Stage; label: string }[] = [
  { id: "write", label: "Write" },
  { id: "sign", label: "Sign" },
  { id: "anchor", label: "Anchor" },
  { id: "prove", label: "Prove" },
];

export interface StudioFlow {
  stage: Stage;
  setStage: (s: Stage) => void;
  prompt: string;
  setPrompt: (p: string) => void;
  provider: "google" | "fixture";
  setProvider: (p: "google" | "fixture") => void;
  model: string;
  setModel: (m: string) => void;
  generatedText: string;
  setGeneratedText: (t: string) => void;
  rawText: string;
  setRawText: (t: string) => void;
  thinkingText: string;
  setThinkingText: (t: string) => void;
  rawThinkingText: string;
  setRawThinkingText: (t: string) => void;
  textHash: string;
  setTextHash: (h: string) => void;
  issuerId: number | "";
  setIssuerId: (id: number | "") => void;
  privateKey: string;
  setPrivateKey: (key: string) => void;
  signerMode: SignerMode;
  setSignerMode: (mode: SignerMode) => void;
  includeEvmProof: boolean;
  setIncludeEvmProof: (include: boolean) => void;
  includeSolanaProof: boolean;
  setIncludeSolanaProof: (include: boolean) => void;
  solanaTxSignature: string;
  setSolanaTxSignature: (sig: string) => void;
  walletProofs: WalletProof[];
  setWalletProofs: (proofs: WalletProof[]) => void;
  signature: string;
  setSignature: (s: string) => void;
  signedAt: number;
  setSignedAt: (t: number) => void;
  nonceHex: string;
  setNonceHex: (n: string) => void;
  bundle: AnchorResponse | null;
  setBundle: (b: AnchorResponse | null) => void;
  verifyClean: VerifyResponse | null;
  setVerifyClean: (v: VerifyResponse | null) => void;
  verifyTampered: VerifyResponse | null;
  setVerifyTampered: (v: VerifyResponse | null) => void;
  tamperedText: string;
  setTamperedText: (t: string) => void;
}
