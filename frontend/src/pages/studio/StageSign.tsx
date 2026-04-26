import { useState } from "react";
import { ethers } from "ethers";
import { motion } from "framer-motion";

import type { StudioFlow } from "./StudioState";
import type { DemoIdentity } from "../../hooks/useDemoIdentity";
import { HashBlock } from "../../components/ui/HashBlock";
import { AddressBlock } from "../../components/ui/AddressBlock";
import { MagneticButton } from "../../components/ui/MagneticButton";
import { EditorialCaption } from "../../components/ui/EditorialCaption";
import { ease } from "../../lib/motion";
import { splitHash } from "../../lib/hash";
import styles from "./Stage.module.css";
import sigStyles from "./StageSign.module.css";

const DOMAIN = {
  name: "Veritext",
  version: "2",
  chainId: 1,
  verifyingContract: "0x0000000000000000000000000000000000000000",
} as const;
const TYPES: Record<string, ethers.TypedDataField[]> = {
  VeritextAnchor: [
    { name: "textHash", type: "bytes32" },
    { name: "issuerId", type: "uint256" },
    { name: "timestamp", type: "uint256" },
    { name: "bundleNonce", type: "bytes32" },
  ],
};

export function StageSign({ flow, identity }: { flow: StudioFlow; identity: DemoIdentity }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onSign = async () => {
    setBusy(true);
    setErr(null);
    try {
      const ts = Math.floor(Date.now() / 1000);
      const nonce = ethers.hexlify(ethers.randomBytes(32));
      const sig = await identity.wallet.signTypedData(DOMAIN, TYPES, {
        textHash: "0x" + flow.textHash,
        issuerId: identity.issuerId,
        timestamp: ts,
        bundleNonce: nonce,
      });
      flow.setSignedAt(ts);
      flow.setNonceHex(nonce.slice(2));
      flow.setSignature(sig);
      setTimeout(() => flow.setStage("anchor"), 800);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.stage}>
      <header className={styles.head}>
        <EditorialCaption number="02" rule>SIGN</EditorialCaption>
        <h2 className={styles.title}>
          Bind it to your <em>identity</em>.
        </h2>
        <p className={styles.lede}>
          Your private key produces a signature over the paragraph&apos;s
          fingerprint. Only your key can make it. Anyone can check it.
        </p>
      </header>

      <div className={sigStyles.cols}>
        <section className={sigStyles.colHash}>
          <HashBlock hex={flow.textHash} label="SHA-256 of the paragraph" />
          <p className={sigStyles.note}>
            One-way fingerprint. If a single character of the text changes,
            this number changes completely.
          </p>
        </section>

        <section className={sigStyles.colIdentity}>
          <span className={sigStyles.idLabel}>Signing as</span>
          <span className={sigStyles.idName}>{identity.name}</span>
          <AddressBlock address={identity.address} label="Address" />
          <span className={sigStyles.idMeta}>Issuer #{identity.issuerId} · ECDSA secp256k1</span>
        </section>
      </div>

      <div className={sigStyles.actions}>
        {!flow.signature ? (
          <MagneticButton onClick={onSign} disabled={busy || !flow.textHash} variant="filled">
            {busy ? "Signing…" : "Sign"}
          </MagneticButton>
        ) : (
          <MagneticButton onClick={() => flow.setStage("anchor")} variant="filled">
            Continue to anchor
          </MagneticButton>
        )}
        <MagneticButton onClick={() => flow.setStage("write")} variant="outline" arrow={false}>
          Back
        </MagneticButton>
        {err && <span className={styles.err}>{err}</span>}
      </div>

      {flow.signature && (
        <motion.div
          className={sigStyles.sigOut}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease }}
        >
          <span className={sigStyles.sigLabel}>Signature (EIP-712)</span>
          <div className={sigStyles.sigGroups}>
            {splitHash(flow.signature, 8).map((g, i) => (
              <motion.span
                key={i}
                className={sigStyles.sigGroup}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease, delay: i * 0.025 }}
              >{g}</motion.span>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
