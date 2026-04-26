import type { AnchorResponse, VerifyResponse } from "../../api/types";

export type Stage = "write" | "sign" | "anchor" | "prove";

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
  textHash: string;
  setTextHash: (h: string) => void;
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
