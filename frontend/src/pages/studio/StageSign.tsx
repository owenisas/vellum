import { useState } from "react";
import { motion } from "framer-motion";

import type { StudioFlow } from "./StudioState";
import { useCompanies } from "../../api/companies";
import { useEcdsa } from "../../hooks/useEcdsa";
import { useEvmWallet } from "../../hooks/useEvmWallet";
import { HashBlock } from "../../components/ui/HashBlock";
import { AddressBlock } from "../../components/ui/AddressBlock";
import { MagneticButton } from "../../components/ui/MagneticButton";
import { EditorialCaption } from "../../components/ui/EditorialCaption";
import { ease } from "../../lib/motion";
import { splitHash } from "../../lib/hash";
import styles from "./Stage.module.css";
import sigStyles from "./StageSign.module.css";

export function StageSign({ flow }: { flow: StudioFlow }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const companies = useCompanies();
  const ecdsa = useEcdsa(flow.privateKey || null);
  const evmWallet = useEvmWallet();
  const selectedCompany = (companies.data ?? []).find((c) => c.issuer_id === Number(flow.issuerId));

  const onSign = async () => {
    setBusy(true);
    setErr(null);
    try {
      if (!flow.issuerId || !selectedCompany) {
        throw new Error("Choose a registered issuer before signing.");
      }
      const ts = Math.floor(Date.now() / 1000);
      let sig: string;
      if (flow.signerMode === "metamask") {
        const signed = await evmWallet.signHash(flow.textHash);
        if (signed.address.toLowerCase() !== selectedCompany.eth_address.toLowerCase()) {
          throw new Error(
            `Connected wallet ${signed.address} does not match issuer ${selectedCompany.eth_address}`,
          );
        }
        sig = signed.signature;
      } else {
        if (!flow.privateKey) throw new Error("Paste the issuer private key or switch to MetaMask.");
        if (ecdsa.address?.toLowerCase() !== selectedCompany.eth_address.toLowerCase()) {
          throw new Error(
            `Local key ${ecdsa.address ?? "(invalid)"} does not match issuer ${selectedCompany.eth_address}`,
          );
        }
        sig = await ecdsa.signHash(flow.textHash);
      }
      flow.setSignedAt(ts);
      flow.setNonceHex(crypto.randomUUID().replace(/-/g, ""));
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
          fingerprint. Use a local demo key or MetaMask; no private key is sent
          to the backend.
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
          <span className={sigStyles.idLabel}>Issuer</span>
          <select
            value={flow.issuerId}
            onChange={(e) => flow.setIssuerId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Choose issuer...</option>
            {(companies.data ?? []).map((c) => (
              <option key={c.id} value={c.issuer_id}>
                {c.name} (#{c.issuer_id})
              </option>
            ))}
          </select>
          {selectedCompany && (
            <>
              <span className={sigStyles.idName}>{selectedCompany.name}</span>
              <AddressBlock address={selectedCompany.eth_address} label="Registered EVM address" />
              <span className={sigStyles.idMeta}>Issuer #{selectedCompany.issuer_id} · EIP-191 personal_sign</span>
            </>
          )}
        </section>
      </div>

      <div className={sigStyles.signerPanel}>
        <label>
          <span className={sigStyles.idLabel}>Issuer signer</span>
          <select
            value={flow.signerMode}
            onChange={(e) => flow.setSignerMode(e.target.value as StudioFlow["signerMode"])}
          >
            <option value="local">Local demo private key</option>
            <option value="metamask">MetaMask / EVM wallet</option>
          </select>
        </label>
        {flow.signerMode === "local" && (
          <label>
            <span className={sigStyles.idLabel}>Private key</span>
            <input
              type="password"
              value={flow.privateKey}
              onChange={(e) => flow.setPrivateKey(e.target.value)}
              placeholder="0x..."
            />
            {ecdsa.address && <span className={sigStyles.idMeta}>Derived address: {ecdsa.address}</span>}
          </label>
        )}
        <div className={sigStyles.proofs}>
          <span className={sigStyles.idLabel}>Optional wallet proofs</span>
          <label>
            <input
              type="checkbox"
              checked={flow.includeEvmProof}
              onChange={(e) => flow.setIncludeEvmProof(e.target.checked)}
            />{" "}
            Attach MetaMask/EVM proof
          </label>
          <label>
            <input
              type="checkbox"
              checked={flow.includeSolanaProof}
              onChange={(e) => flow.setIncludeSolanaProof(e.target.checked)}
            />{" "}
            Attach Phantom/Solana proof
          </label>
          {flow.includeSolanaProof && (
            <input
              type="text"
              value={flow.solanaTxSignature}
              onChange={(e) => flow.setSolanaTxSignature(e.target.value)}
              placeholder="Optional existing Solana Memo tx signature"
            />
          )}
          <span className={sigStyles.idMeta}>
            Wallet proofs are message signatures only. They do not cost gas/SOL,
            submit transactions, or grant backend access to funds.
          </span>
        </div>
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
          <span className={sigStyles.sigLabel}>Signature (EIP-191 personal_sign)</span>
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
