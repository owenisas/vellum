import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "react-router-dom";

import { useAuth } from "../auth/useAuth";
import { useCompanies } from "../api/companies";
import { StageIndicator } from "../components/ui/StageIndicator";
import { EditorialCaption } from "../components/ui/EditorialCaption";
import { AddressBlock } from "../components/ui/AddressBlock";
import { Button } from "../components/ui/Button";
import { ease } from "../lib/motion";
import { copy } from "../lib/hash";

import { STAGES, type Stage, type StudioFlow } from "./studio/StudioState";
import { StageWrite } from "./studio/StageWrite";
import { StageSign } from "./studio/StageSign";
import { StageAnchor } from "./studio/StageAnchor";
import { StageProve } from "./studio/StageProve";

import type { AnchorResponse, VerifyResponse, WalletProof } from "../api/types";
import styles from "./Studio.module.css";

const DEFAULT_PROMPT = "In one short paragraph, explain why text provenance matters for AI-generated content.";

function downloadJson(filename: string, obj: unknown) {
  trigger(filename, new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" }));
}
function downloadText(filename: string, text: string) {
  trigger(filename, new Blob([text], { type: "text/plain" }));
}
function trigger(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

export function Studio() {
  const auth = useAuth();
  const companies = useCompanies();
  const [params, setParams] = useSearchParams();

  const [stage, setStageState] = useState<Stage>(() => {
    const fromUrl = params.get("stage");
    if (fromUrl && STAGES.find((s) => s.id === fromUrl)) return fromUrl as Stage;
    return "write";
  });
  const setStage = (s: Stage) => {
    setStageState(s);
    setParams({ stage: s }, { replace: true });
    requestAnimationFrame(() => {
      const el = document.getElementById(`stage-${s}`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [provider, setProvider] = useState<"google" | "fixture">("fixture");
  const [model, setModel] = useState<string>("gemma-4-27b-it");
  const [generatedText, setGeneratedText] = useState<string>("");
  const [rawText, setRawText] = useState<string>("");
  const [textHash, setTextHash] = useState<string>("");
  const [issuerId, setIssuerId] = useState<number | "">("");
  const [privateKey, setPrivateKey] = useState<string>("");
  const [signerMode, setSignerMode] = useState<"local" | "metamask">("local");
  const [includeEvmProof, setIncludeEvmProof] = useState(false);
  const [includeSolanaProof, setIncludeSolanaProof] = useState(false);
  const [solanaTxSignature, setSolanaTxSignature] = useState("");
  const [walletProofs, setWalletProofs] = useState<WalletProof[]>([]);
  const [signature, setSignature] = useState<string>("");
  const [signedAt, setSignedAt] = useState<number>(0);
  const [nonceHex, setNonceHex] = useState<string>("");
  const [bundle, setBundle] = useState<AnchorResponse | null>(null);
  const [verifyClean, setVerifyClean] = useState<VerifyResponse | null>(null);
  const [verifyTampered, setVerifyTampered] = useState<VerifyResponse | null>(null);
  const [tamperedText, setTamperedText] = useState<string>("");

  const flow: StudioFlow = useMemo(
    () => ({
      stage, setStage,
      prompt, setPrompt,
      provider, setProvider,
      model, setModel,
      generatedText, setGeneratedText,
      rawText, setRawText,
      textHash, setTextHash,
      issuerId, setIssuerId,
      privateKey, setPrivateKey,
      signerMode, setSignerMode,
      includeEvmProof, setIncludeEvmProof,
      includeSolanaProof, setIncludeSolanaProof,
      solanaTxSignature, setSolanaTxSignature,
      walletProofs, setWalletProofs,
      signature, setSignature,
      signedAt, setSignedAt,
      nonceHex, setNonceHex,
      bundle, setBundle,
      verifyClean, setVerifyClean,
      verifyTampered, setVerifyTampered,
      tamperedText, setTamperedText,
    }),
    [stage, prompt, provider, model, generatedText, rawText, textHash, issuerId, privateKey, signerMode, includeEvmProof, includeSolanaProof, solanaTxSignature, walletProofs, signature, signedAt, nonceHex, bundle, verifyClean, verifyTampered, tamperedText],
  );

  if (auth.isLoading) {
    return (
      <section className={`container ${styles.boot}`}>
        <EditorialCaption number="00" rule>Studio</EditorialCaption>
        <h2 className={styles.bootTitle}>Checking agent access...</h2>
        <p className={styles.bootBody}>
          Vellum is preparing the Auth0-secured provenance workflow.
        </p>
      </section>
    );
  }
  if (!auth.isAuthenticated) {
    return (
      <section className={`container ${styles.boot}`}>
        <EditorialCaption number="00" rule>Studio</EditorialCaption>
        <h2 className={styles.bootTitle}>Sign in to run the agent.</h2>
        <p className={styles.bootBody}>
          Generation and anchoring are protected actions. Auth0 identity is written
          into the proof bundle as the authorized agent actor.
        </p>
        <Button onClick={auth.login}>Log in with Auth0</Button>
      </section>
    );
  }

  const selectedIssuer = (companies.data ?? []).find((c) => c.issuer_id === Number(issuerId));
  const hintExplorer = bundle?.proof_bundle_v2?.verification_hints?.explorer_url;
  const explorerUrl = (typeof hintExplorer === "string" ? hintExplorer : null)
    ?? (bundle?.chain_receipt?.solana_tx_signature
      ? `https://explorer.solana.com/tx/${bundle.chain_receipt.solana_tx_signature}?cluster=devnet`
      : null);

  return (
    <motion.section
      key="studio"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4, ease }}
      className={`container ${styles.shell}`}
    >
      <header className={styles.top}>
        <div className={styles.identity}>
          <span className={styles.identityCap}>Signed in as</span>
          <span className={styles.identityName}>
            {auth.user?.name ?? auth.user?.email ?? "Authenticated user"}
          </span>
          {selectedIssuer ? (
            <AddressBlock address={selectedIssuer.eth_address} className={styles.identityAddr} />
          ) : (
            <span className={styles.identityAddr}>Choose an issuer in Sign.</span>
          )}
          {!auth.demo && <Button variant="link" size="sm" onClick={auth.logout}>Log out</Button>}
        </div>
        <StageIndicator
          stages={STAGES}
          current={stage}
          onJump={(s) => setStage(s as Stage)}
          className={styles.indicator}
        />
      </header>

      <div id="stage-write"><StageWrite flow={flow} /></div>
      {flow.generatedText && (<div id="stage-sign"><StageSign flow={flow} /></div>)}
      {flow.signature && (<div id="stage-anchor"><StageAnchor flow={flow} /></div>)}
      {flow.bundle && (<div id="stage-prove"><StageProve flow={flow} /></div>)}

      <AnimatePresence>
        {bundle && (
          <motion.div
            className={styles.footBar}
            initial={{ y: 64, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 64, opacity: 0 }}
            transition={{ duration: 0.5, ease }}
          >
            <div className={styles.footInner}>
              <span className={styles.footLabel}>Take it with you</span>
              <Button variant="ghost" size="sm" onClick={() => downloadJson("bundle.json", bundle.proof_bundle_v2)}>
                bundle.json
              </Button>
              <Button variant="ghost" size="sm" onClick={() => downloadText("text.txt", generatedText)}>
                text.txt
              </Button>
              <Button variant="ghost" size="sm" onClick={() => copy("veritext-verify --bundle ./bundle.json --text ./text.txt")}>
                copy CLI
              </Button>
              {explorerUrl && (
                <a className={`link-u ${styles.footLink}`} href={explorerUrl} target="_blank" rel="noreferrer noopener">
                  Solana Explorer ↗
                </a>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}
