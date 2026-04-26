import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "react-router-dom";

import { useDemoIdentity } from "../hooks/useDemoIdentity";
import { useDemoMeta } from "../api/demo";
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

import type { AnchorResponse, VerifyResponse } from "../api/types";
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
  const { status, reset } = useDemoIdentity();
  const { data: meta } = useDemoMeta();
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
  const [model, setModel] = useState<string>("fixture");
  const [generatedText, setGeneratedText] = useState<string>("");
  const [textHash, setTextHash] = useState<string>("");
  const [signature, setSignature] = useState<string>("");
  const [signedAt, setSignedAt] = useState<number>(0);
  const [nonceHex, setNonceHex] = useState<string>("");
  const [bundle, setBundle] = useState<AnchorResponse | null>(null);
  const [verifyClean, setVerifyClean] = useState<VerifyResponse | null>(null);
  const [verifyTampered, setVerifyTampered] = useState<VerifyResponse | null>(null);
  const [tamperedText, setTamperedText] = useState<string>("");

  useEffect(() => {
    if (!meta) return;
    if (meta.providers_available.includes("google")) {
      setProvider("google");
      setModel("gemma-3-12b-it");
    }
  }, [meta]);

  const flow: StudioFlow = useMemo(
    () => ({
      stage, setStage,
      prompt, setPrompt,
      provider, setProvider,
      model, setModel,
      generatedText, setGeneratedText,
      textHash, setTextHash,
      signature, setSignature,
      signedAt, setSignedAt,
      nonceHex, setNonceHex,
      bundle, setBundle,
      verifyClean, setVerifyClean,
      verifyTampered, setVerifyTampered,
      tamperedText, setTamperedText,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [stage, prompt, provider, model, generatedText, textHash, signature, signedAt, nonceHex, bundle, verifyClean, verifyTampered, tamperedText],
  );

  if (status.state === "loading") {
    return (
      <section className={`container ${styles.boot}`}>
        <EditorialCaption number="00" rule>Studio</EditorialCaption>
        <h2 className={styles.bootTitle}>Bootstrapping a one-time identity…</h2>
        <p className={styles.bootBody}>
          Generating an ephemeral keypair in your browser. No accounts, no setup.
        </p>
      </section>
    );
  }
  if (status.state === "error") {
    return (
      <section className={`container ${styles.boot}`}>
        <EditorialCaption number="00" rule>Studio</EditorialCaption>
        <h2 className={styles.bootTitle}>Studio is offline.</h2>
        <p className={styles.bootBody}>{status.error}</p>
        <p className={styles.bootBody}>Make sure the backend at <code>/api/demo/auto-register</code> is running.</p>
      </section>
    );
  }

  const id = status.identity;
  const explorerUrl = bundle?.proof_bundle_v2?.verification_hints?.explorer_url
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
          <span className={styles.identityName}>{id.name}</span>
          <AddressBlock address={id.address} className={styles.identityAddr} />
          <Button variant="link" size="sm" onClick={reset}>Reset identity</Button>
        </div>
        <StageIndicator
          stages={STAGES}
          current={stage}
          onJump={(s) => setStage(s as Stage)}
          className={styles.indicator}
        />
      </header>

      <div id="stage-write"><StageWrite flow={flow} identity={id} /></div>
      {flow.generatedText && (<div id="stage-sign"><StageSign flow={flow} identity={id} /></div>)}
      {flow.signature && (<div id="stage-anchor"><StageAnchor flow={flow} identity={id} /></div>)}
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
