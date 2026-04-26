import { useCallback, useState } from "react";
import type { WalletProof } from "../api/types";
import { buildWalletMessage } from "./walletMessages";

type SolanaProvider = {
  isPhantom?: boolean;
  publicKey?: { toString: () => string };
  connect: () => Promise<{ publicKey: { toString: () => string } }>;
  signMessage?: (
    message: Uint8Array,
    encoding?: "utf8",
  ) => Promise<{ signature: Uint8Array }>;
};

declare global {
  interface Window {
    solana?: SolanaProvider;
  }
}

function toBase64(bytes: Uint8Array) {
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

export function useSolanaWallet() {
  const [address, setAddress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    if (!window.solana) {
      throw new Error("Phantom or another Solana wallet is not available");
    }
    setError(null);
    try {
      const resp = await window.solana.connect();
      const nextAddress = resp.publicKey.toString();
      setAddress(nextAddress);
      return { address: nextAddress, provider: window.solana };
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to connect Solana wallet";
      setError(msg);
      throw e;
    }
  }, []);

  const buildProof = useCallback(
    async (hashHex: string, txSignature?: string): Promise<WalletProof> => {
      const { address: nextAddress, provider } = await connect();
      if (!provider.signMessage) {
        throw new Error("Connected Solana wallet does not support message signing");
      }
      const message = buildWalletMessage(hashHex, "solana", nextAddress);
      const encoded = new TextEncoder().encode(message);
      const signed = await provider.signMessage(encoded, "utf8");
      return {
        wallet_type: "solana",
        address: nextAddress,
        message,
        signature: toBase64(signed.signature),
        signature_encoding: "base64",
        cluster: "devnet",
        tx_signature: txSignature?.trim() || null,
      };
    },
    [connect],
  );

  return {
    address,
    error,
    connect,
    buildProof,
  };
}
