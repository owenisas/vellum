import { useQuery } from "@tanstack/react-query";

import { get, post } from "./client";

export interface DemoIdentity {
  auth0_enabled: boolean;
  demo_mode: "live" | "fixture";
  chain_backend: "simulated" | "solana";
  anchor_strategy: "per_response" | "merkle_batch";
  providers_available: string[];
}

export interface AutoRegisterResponse {
  issuer_id: number;
  name: string;
  eth_address: string;
  public_key_hex: string;
  current_key_id: number;
}

export const demoApi = {
  identity: () => get<DemoIdentity>("/api/demo/identity"),
  autoRegister: (eth_address: string, name?: string) =>
    post<AutoRegisterResponse>("/api/demo/auto-register", { eth_address, name }),
  samplePrompts: () => get<{ prompts: string[] }>("/api/demo/sample-prompts"),
};

export const useDemoMeta = () =>
  useQuery({ queryKey: ["demo", "identity"], queryFn: demoApi.identity, staleTime: 60_000 });

export const useSamplePrompts = () =>
  useQuery({
    queryKey: ["demo", "sample-prompts"],
    queryFn: demoApi.samplePrompts,
    staleTime: 5 * 60_000,
  });
