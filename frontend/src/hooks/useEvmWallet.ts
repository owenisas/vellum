import { BrowserProvider } from "ethers";
import { useCallback, useState } from "react";
import type { WalletProof } from "../api/types";
import { buildWalletMessage } from "./walletMessages";

type EthereumProvider = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
};

declare global {
  interface Window {
    ethereum?: EthereumProvider;
  }
}

export function useEvmWallet() {
  const [address, setAddress] = useState<string | null>(null);
  const [chainId, setChainId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    if (!window.ethereum) {
      throw new Error("MetaMask or another EVM wallet is not available");
    }
    setError(null);
    try {
      const provider = new BrowserProvider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      const signer = await provider.getSigner();
      const network = await provider.getNetwork();
      const nextAddress = await signer.getAddress();
      setAddress(nextAddress);
      setChainId(network.chainId.toString());
      return { address: nextAddress, chainId: network.chainId.toString(), signer };
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to connect EVM wallet";
      setError(msg);
      throw e;
    }
  }, []);

  const signHash = useCallback(
    async (hashHex: string) => {
      const { address: nextAddress, signer } = await connect();
      const signature = await signer.signMessage(hashHex);
      return { address: nextAddress, signature };
    },
    [connect],
  );

  const buildProof = useCallback(
    async (hashHex: string): Promise<WalletProof> => {
      const { address: nextAddress, chainId: nextChainId, signer } = await connect();
      const message = buildWalletMessage(hashHex, "evm", nextAddress);
      const signature = await signer.signMessage(message);
      return {
        wallet_type: "evm",
        address: nextAddress,
        message,
        signature,
        signature_encoding: "hex",
        chain_id: nextChainId,
      };
    },
    [connect],
  );

  return {
    address,
    chainId,
    error,
    connect,
    signHash,
    buildProof,
  };
}
