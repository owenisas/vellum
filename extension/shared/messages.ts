import type { VerifyResult } from "./api.js";

export interface ScanPayloadSummary {
  schemaVersion: number;
  issuerId: number;
  modelId: number;
  modelVersionId: number;
  keyId: number;
  crc: number;
  crcValid: boolean;
  rawPayloadHex: string;
}

export interface CandidateText {
  id: string;
  text: string;
  preview: string;
  payload: ScanPayloadSummary;
}

export interface ScanResultMessage {
  type: "vellum:scan-result";
  count: number;
  invalidCount: number;
  payloads: ScanPayloadSummary[];
  candidates: CandidateText[];
  selectionText: string;
  url: string;
}

export interface ScanState {
  count: number;
  invalidCount: number;
  payloads: ScanPayloadSummary[];
  candidates: CandidateText[];
  selectionText: string;
  url: string;
  updatedAt: number;
  verification: VerificationState | null;
}

export interface VerificationState {
  source: "selection" | "candidate";
  textPreview: string;
  payloadHex?: string;
  result: VerifyResult;
}

export interface GetStateMessage {
  type: "vellum:get-state";
  tabId?: number;
}

export interface RescanMessage {
  type: "vellum:rescan";
}

export interface VerifyTextMessage {
  type: "vellum:verify-text";
  tabId: number;
  source: "selection" | "candidate";
  text: string;
  textPreview: string;
  payloadHex?: string;
}

export interface MarkVerifiedMessage {
  type: "vellum:mark-verified";
  payloadHex?: string;
  verified: boolean;
  label: string;
}

export interface SettingsMessage {
  type: "vellum:set-api-base-url";
  apiBaseUrl: string;
}

export interface GetSettingsMessage {
  type: "vellum:get-settings";
}

export type RuntimeMessage =
  | ScanResultMessage
  | GetStateMessage
  | RescanMessage
  | VerifyTextMessage
  | MarkVerifiedMessage
  | SettingsMessage
  | GetSettingsMessage;

export const previewText = (text: string, maxLength = 180): string => {
  const compact = text.replace(/\s+/g, " ").trim();
  if (compact.length <= maxLength) return compact;
  return `${compact.slice(0, maxLength - 1)}...`;
};
