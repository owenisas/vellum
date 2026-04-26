import { useState } from "react";
import { motion } from "framer-motion";

import type { StudioFlow } from "./StudioState";
import type { DemoIdentity } from "../../hooks/useDemoIdentity";
import { useAnchor } from "../../api/registry";
import { MagneticButton } from "../../components/ui/MagneticButton";
import { EditorialCaption } from "../../components/ui/EditorialCaption";
import { MerkleTreeScene } from "../../components/scenes/MerkleTreeScene";
import { ease } from "../../lib/motion";
import { shortAddress } from "../../lib/hash";
import styles from "./Stage.module.css";
import anchorStyles from "./StageAnchor.module.css";

export function StageAnchor({ flow, identity }: { flow: StudioFlow; identity: DemoIdentity }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const anchor = useAnchor();

  const onAnchor = async () => {
    setBusy(true);
    setErr(null);
    try {
      const res = await anchor.mutateAsync({
        text: flow.generatedText,
        issuer_id: identity.issuerId,
        signature_hex: flow.signature,
        sig_scheme: "eip712",
        timestamp: flow.signedAt,
        bundle_nonce_hex: flow.nonceHex,
      });
      flow.setBundle(res);
      setTimeout(() => flow.setStage("prove"), 1100);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const sealed = !!flow.bundle;
  const explorerUrl = flow.bundle?.proof_bundle_v2?.verification_hints?.explorer_url
    ?? (flow.bundle?.chain_receipt?.solana_tx_signature
      ? `https://explorer.solana.com/tx/${flow.bundle.chain_receipt.solana_tx_signature}?cluster=devnet`
      : null);

  return (
    <div className={styles.stage}>
      <header className={styles.head}>
        <EditorialCaption number="03" rule>ANCHOR</EditorialCaption>
        <h2 className={styles.title}>
          Seal it onto a <em>public ledger</em>.
        </h2>
        <p className={styles.lede}>
          The signed paragraph joins a Merkle tree of recently sealed sentences.
          Its root is broadcast to Solana — a public record no one can rewrite.
        </p>
      </header>

      <div className={anchorStyles.scene}>
        <MerkleTreeScene leafCount={8} highlightLeaf={2} sealed={sealed} />
      </div>

      {!sealed ? (
        <div className={anchorStyles.actions}>
          <MagneticButton onClick={onAnchor} disabled={busy || !flow.signature} variant="filled">
            {busy ? "Sealing on Solana…" : "Anchor on chain"}
          </MagneticButton>
          <MagneticButton onClick={() => flow.setStage("sign")} variant="outline" arrow={false}>
            Back
          </MagneticButton>
          {err && <span className={styles.err}>{err}</span>}
        </div>
      ) : (
        <motion.div
          className={anchorStyles.receipt}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease, delay: 0.3 }}
        >
          <span className={anchorStyles.recLabel}>Receipt</span>
          <dl className={anchorStyles.recList}>
            <Row k="Block" v={`#${flow.bundle?.chain_receipt.block_num}`} />
            <Row k="Status" v={flow.bundle?.bundle_status ?? ""} accent />
            <Row k="Scheme" v={flow.bundle?.proof_bundle_v2.signature.scheme ?? ""} />
            <Row k="Canonical form" v={flow.bundle?.proof_bundle_v2.signature.canonicalization ?? ""} />
            <Row k="Signed by" v={shortAddress(flow.bundle?.eth_address ?? "", 8, 6)} />
            <Row k="Tx hash" v={shortAddress(flow.bundle?.chain_receipt.tx_hash ?? "", 10, 8)} />
            {flow.bundle?.chain_receipt.solana_tx_signature && (
              <Row k="Solana" v={shortAddress(flow.bundle.chain_receipt.solana_tx_signature, 10, 8)} />
            )}
          </dl>
          <div className={anchorStyles.recActions}>
            <MagneticButton onClick={() => flow.setStage("prove")} variant="filled">Prove it</MagneticButton>
            {explorerUrl && (
              <MagneticButton href={explorerUrl} variant="outline">View on Solana Explorer</MagneticButton>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}

function Row({ k, v, accent }: { k: string; v: string; accent?: boolean }) {
  return (
    <>
      <dt>{k}</dt>
      <dd className={accent ? anchorStyles.accent : ""}>{v}</dd>
    </>
  );
}
