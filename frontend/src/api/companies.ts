import { useMutation, useQuery } from "@tanstack/react-query";

import { get, post } from "./client";

export interface Company {
  id: number;
  name: string;
  issuer_id: number;
  eth_address: string;
  public_key_hex: string;
  current_key_id: number;
  key_history: KeyHistoryEntry[];
  active: boolean;
  created_at: string;
}

export interface KeyHistoryEntry {
  key_id: number;
  eth_address: string;
  public_key_hex: string;
  active_from: string;
  active_until?: string | null;
}

export interface RotateKeyRequest {
  new_eth_address: string;
  new_public_key_hex: string;
  grace_period_days: number;
}

export const companiesApi = {
  list: () => get<Company[]>("/api/companies"),
  create: (body: Partial<Company> & { admin_secret?: string }) => post<Company>("/api/companies", body),
  rotateKey: (issuer_id: number, body: RotateKeyRequest) =>
    post<{ issuer_id: number; old_key_id: number; new_key_id: number; grace_until: string }>(
      `/api/companies/${issuer_id}/rotate-key`,
      body,
    ),
};

export const useCompanies = () => useQuery({ queryKey: ["companies"], queryFn: companiesApi.list });
export const useCreateCompany = () => useMutation({ mutationFn: companiesApi.create });
export const useRotateKey = (issuer_id: number) =>
  useMutation({ mutationFn: (body: RotateKeyRequest) => companiesApi.rotateKey(issuer_id, body) });
