import { useCallback, useState } from "react";
import { Wallet, sha256, toUtf8Bytes } from "ethers";

/** Hash + sign hooks built on ethers.js. */
export function useEcdsa(privateKeyHex: string | null) {
  const [error, setError] = useState<string | null>(null);

  const wallet = privateKeyHex
    ? (() => {
        try {
          return new Wallet(
            privateKeyHex.startsWith("0x") ? privateKeyHex : `0x${privateKeyHex}`,
          );
        } catch (e) {
          // eslint-disable-next-line no-console
          console.warn("invalid private key", e);
          return null;
        }
      })()
    : null;

  const hashText = useCallback((text: string): string => {
    // sha256(utf8(text)) — matches the Python `hash_text`
    return sha256(toUtf8Bytes(text)).slice(2); // strip 0x to match server hex
  }, []);

  const signHash = useCallback(
    async (hashHex: string): Promise<string> => {
      if (!wallet) throw new Error("No private key available");
      // Sign the hex string AS A TEXT MESSAGE — matches eth_account.encode_defunct(text=hash)
      // server-side.
      const sig = await wallet.signMessage(hashHex);
      return sig;
    },
    [wallet],
  );

  const signText = useCallback(
    async (text: string): Promise<{ hash: string; signature: string }> => {
      try {
        setError(null);
        const hash = hashText(text);
        const signature = await signHash(hash);
        return { hash, signature };
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
        throw e;
      }
    },
    [hashText, signHash],
  );

  return {
    address: wallet?.address ?? null,
    hashText,
    signHash,
    signText,
    error,
  };
}
