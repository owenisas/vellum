import { useEffect, useState } from "react";
import { ethers } from "ethers";

import { demoApi } from "../api/demo";

const PKEY_STORAGE_KEY = "vt_demo_pkey";
const ISSUER_STORAGE_KEY = "vt_demo_issuer";

export interface DemoIdentity {
  /** ethers Wallet instance — has signTypedData / signMessage */
  wallet: ethers.Wallet;
  /** 0x-prefixed checksummed address */
  address: string;
  /** raw 0x-prefixed private key (kept in localStorage for the demo) */
  privateKey: string;
  /** Backend-assigned 12-bit issuer id */
  issuerId: number;
  /** Display name returned by /api/demo/auto-register */
  name: string;
}

export type IdentityStatus =
  | { state: "loading" }
  | { state: "ready"; identity: DemoIdentity }
  | { state: "error"; error: string };

/**
 * One-click demo identity:
 *  1. On mount, look up an ephemeral private key in localStorage; create one if missing.
 *  2. POST /api/demo/auto-register with the wallet address; cache the assigned issuer_id.
 *  3. Return a ready DemoIdentity for the rest of the page to use.
 *
 * No MetaMask. No admin secret. Reset() wipes both keys + asks for a new identity.
 */
export function useDemoIdentity(): {
  status: IdentityStatus;
  reset: () => void;
} {
  const [status, setStatus] = useState<IdentityStatus>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Step 1: load or create wallet
        let pkey = localStorage.getItem(PKEY_STORAGE_KEY);
        if (!pkey) {
          const w = ethers.Wallet.createRandom();
          pkey = w.privateKey;
          localStorage.setItem(PKEY_STORAGE_KEY, pkey);
        }
        const wallet = new ethers.Wallet(pkey);

        // Step 2: load or create issuer
        let cachedIssuerJson = localStorage.getItem(ISSUER_STORAGE_KEY);
        let assigned: { issuer_id: number; name: string } | null = null;
        if (cachedIssuerJson) {
          try {
            const c = JSON.parse(cachedIssuerJson);
            if (c?.address?.toLowerCase() === wallet.address.toLowerCase()) {
              assigned = { issuer_id: c.issuer_id, name: c.name };
            }
          } catch {
            // bad cache; fall through to register
          }
        }
        if (!assigned) {
          const r = await demoApi.autoRegister(wallet.address);
          assigned = { issuer_id: r.issuer_id, name: r.name };
          localStorage.setItem(
            ISSUER_STORAGE_KEY,
            JSON.stringify({ address: wallet.address, ...assigned }),
          );
        }

        if (cancelled) return;
        setStatus({
          state: "ready",
          identity: {
            wallet,
            address: wallet.address,
            privateKey: wallet.privateKey,
            issuerId: assigned.issuer_id,
            name: assigned.name,
          },
        });
      } catch (err) {
        if (cancelled) return;
        setStatus({
          state: "error",
          error: err instanceof Error ? err.message : "failed to bootstrap demo identity",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function reset() {
    localStorage.removeItem(PKEY_STORAGE_KEY);
    localStorage.removeItem(ISSUER_STORAGE_KEY);
    window.location.reload();
  }

  return { status, reset };
}
