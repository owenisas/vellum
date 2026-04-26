import { useState } from "react";
import { ethers } from "ethers";

const VERITEXT_DOMAIN = {
  name: "Veritext",
  version: "2",
  chainId: 1,
  verifyingContract: "0x0000000000000000000000000000000000000000",
} as const;

const VERITEXT_TYPES = {
  VeritextAnchor: [
    { name: "textHash", type: "bytes32" },
    { name: "issuerId", type: "uint256" },
    { name: "timestamp", type: "uint256" },
    { name: "bundleNonce", type: "bytes32" },
  ],
} as const;

export interface AnchorMessage {
  textHash: string; // 0x... 32 bytes
  issuerId: number;
  timestamp: number;
  bundleNonce: string; // 0x... 32 bytes
}

export function useEcdsa() {
  const [error, setError] = useState<Error | null>(null);

  // EIP-712 path. Falls back to EIP-191 personal_sign if signTypedData throws.
  async function signWithKey(
    message: AnchorMessage,
    privateKeyHex: string,
  ): Promise<{ signatureHex: string; scheme: "eip712" | "eip191_personal_sign" }> {
    try {
      const wallet = new ethers.Wallet(privateKeyHex);
      const sig = await wallet.signTypedData(VERITEXT_DOMAIN, VERITEXT_TYPES, message);
      return { signatureHex: sig, scheme: "eip712" };
    } catch (err) {
      // Fall back to EIP-191
      const wallet = new ethers.Wallet(privateKeyHex);
      const sig = await wallet.signMessage(ethers.getBytes(message.textHash));
      setError(err instanceof Error ? err : new Error("eip712 failed; used eip191"));
      return { signatureHex: sig, scheme: "eip191_personal_sign" };
    }
  }

  function sha256Hex(text: string): string {
    // Use SubtleCrypto when available; ethers' keccak256 isn't sha256.
    return _sha256Hex(text);
  }

  return { signWithKey, sha256Hex, error };
}

async function _sha256HexAsync(text: string): Promise<string> {
  const enc = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", enc);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// Synchronous wrapper used in places where we already have the digest. For the
// async path callers should use the helper directly.
function _sha256Hex(_text: string): string {
  throw new Error("use _sha256HexAsync");
}

export { _sha256HexAsync as sha256HexAsync };
