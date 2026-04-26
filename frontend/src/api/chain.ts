import { useQuery } from "@tanstack/react-query";

import { get } from "./client";

export interface ChainStatus {
  chain_type: string;
  anchor_strategy: string;
  block_count: number;
  latest_block_num?: number;
  latest_tx_hash?: string;
  pending_batch_size: number;
}

export interface ChainBlock {
  block_num: number;
  prev_hash: string;
  tx_hash: string;
  data_hash: string;
  issuer_id: number;
  signature_hex: string;
  timestamp: string;
  solana_tx_signature?: string | null;
}

export const chainApi = {
  status: () => get<ChainStatus>("/api/chain/status"),
  blocks: (limit = 50, offset = 0) =>
    get<ChainBlock[]>(`/api/chain/blocks?limit=${limit}&offset=${offset}`),
};

export const useChainStatus = () => useQuery({ queryKey: ["chain", "status"], queryFn: chainApi.status });
export const useChainBlocks = (limit = 50) =>
  useQuery({ queryKey: ["chain", "blocks", limit], queryFn: () => chainApi.blocks(limit, 0) });
