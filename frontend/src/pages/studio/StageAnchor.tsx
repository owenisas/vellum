import { useState } from "react";
import { motion } from "framer-motion";

import type { WalletProof } from "../../api/types";
import type { StudioFlow } from "./StudioState";
import { useAnchor } from "../../api/registry";
import { useEvmWallet } from "../../hooks/useEvmWallet";
import { useSolanaWallet } from "../../hooks/useSolanaWallet";
import { MagneticButton } from "../../components/ui/MagneticButton";
import { EditorialCaption } from "../../components/ui/EditorialCaption";
import { MerkleTreeScene } from "../../components/scenes/MerkleTreeScene";
import { ease } from "../../lib/motion";
import { copy, shortAddress } from "../../lib/hash";
import styles from "./Stage.module.css";
import anchorStyles from "./StageAnchor.module.css";

export function StageAnchor({ flow }: { flow: StudioFlow }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const anchor = useAnchor();
  const evmWallet = useEvmWallet();
  const solanaWallet = useSolanaWallet();

  const onAnchor = async () => {
    setBusy(true);
    setErr(null);
    try {
      if (!flow.issuerId) throw new Error("Choose and sign with an issuer first.");
      const walletProofs: WalletProof[] = [];
      if (flow.includeEvmProof) {
        walletProofs.push(await evmWallet.buildProof(flow.textHash));
      }
      if (flow.includeSolanaProof) {
        walletProofs.push(await solanaWallet.buildProof(flow.textHash, flow.solanaTxSignature));
      }
      flow.setWalletProofs(walletProofs);
      const res = await anchor.mutateAsync({
        text: flow.generatedText,
        raw_text: flow.rawText || flow.generatedText,
        issuer_id: Number(flow.issuerId),
        signature_hex: flow.signature,
        metadata: {
          provider: flow.provider,
          model: flow.model,
          signed_at: flow.signedAt,
          bundle_nonce_hex: flow.nonceHex,
          issuer_signer: flow.signerMode,
        },
        wallet_proofs: walletProofs,
        wm_params: { issuer_id: Number(flow.issuerId), model_id: 1, model_version_id: 1, key_id: 1 },
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
  const hintExplorer = flow.bundle?.proof_bundle_v2?.verification_hints?.explorer_url;
  const explorerUrl = (typeof hintExplorer === "string" ? hintExplorer : null)
    ?? (flow.bundle?.chain_receipt?.solana_tx_signature
      ? `https://explorer.solana.com/tx/${flow.bundle.chain_receipt.solana_tx_signature}?cluster=devnet`
      : null);
  const onCopySignedText = async () => {
    const ok = await copy(flow.generatedText);
    setCopyState(ok ? "copied" : "failed");
    window.setTimeout(() => setCopyState("idle"), 1800);
  };

  return (
    <div className={styles.stage}>
      <header className={styles.head}>
        <EditorialCaption number="03" rule>ANCHOR</EditorialCaption>
        <h2 className={styles.title}>
          Seal it into a <em>verifiable registry</em>.
        </h2>
        <p className={styles.lede}>
          The signed paragraph joins a Merkle tree of recently sealed sentences.
          For this no-funds demo, browser wallet signatures prove wallet control
          while the backend records a tamper-evident registry receipt without
          requiring gas, SOL, or a server fee-payer wallet.
        </p>
      </header>

      <div className={anchorStyles.scene}>
        <MerkleTreeScene leafCount={8} highlightLeaf={2} sealed={sealed} />
      </div>

      {!sealed ? (
        <div className={anchorStyles.actions}>
          <MagneticButton onClick={onAnchor} disabled={busy || !flow.signature} variant="filled">
            {busy ? "Sealing in registry..." : "Anchor without funds"}
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
            <Row k="Status" v="verified" accent />
            <Row k="Scheme" v={String(flow.bundle?.proof_bundle_v2.signature.scheme ?? "")} />
            <Row k="Canonical form" v={String(flow.bundle?.proof_bundle_v2.signature.canonicalization ?? "")} />
            <Row k="Signed by" v={shortAddress(flow.bundle?.eth_address ?? "", 8, 6)} />
            <Row k="Tx hash" v={shortAddress(flow.bundle?.chain_receipt.tx_hash ?? "", 10, 8)} />
            {(flow.bundle?.proof_bundle_v2.wallet_proofs ?? []).length > 0 && (
              <Row
                k="Wallet proofs"
                v={(flow.bundle?.proof_bundle_v2.wallet_proofs ?? [])
                  .map((p) => `${String(p.wallet_type ?? "wallet")}:${shortAddress(String(p.address ?? ""), 6, 4)}`)
                  .join(", ")}
              />
            )}
            {flow.bundle?.chain_receipt.solana_tx_signature && (
              <Row k="Solana" v={shortAddress(flow.bundle.chain_receipt.solana_tx_signature, 10, 8)} />
            )}
          </dl>
          <div className={anchorStyles.recActions}>
            <MagneticButton onClick={onCopySignedText} variant="filled">
              {copyState === "copied" ? "Copied signed text" : copyState === "failed" ? "Copy failed" : "Copy signed text"}
            </MagneticButton>
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
