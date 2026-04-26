import { get } from "./client";
import type { ChainBlock, ChainStatus } from "./types";
import { useQuery } from "@tanstack/react-query";

export const chainApi = {
  status: () => get<ChainStatus>("/api/chain/status"),
  blocks: (limit = 50, offset = 0) =>
    get<ChainBlock[]>(`/api/chain/blocks?limit=${limit}&offset=${offset}`),
  block: (block_num: number) => get<ChainBlock>(`/api/chain/blocks/${block_num}`),
};

export function useChainStatus() {
  return useQuery({
    queryKey: ["chain", "status"],
    queryFn: chainApi.status,
    refetchInterval: 30_000,
  });
}

export function useChainBlocks(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ["chain", "blocks", limit, offset],
    queryFn: () => chainApi.blocks(limit, offset),
    refetchInterval: 30_000,
  });
}
