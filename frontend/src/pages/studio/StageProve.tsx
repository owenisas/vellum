import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import type { StudioFlow } from "./StudioState";
import { useVerify } from "../../api/registry";
import { MagneticButton } from "../../components/ui/MagneticButton";
import { EditorialCaption } from "../../components/ui/EditorialCaption";
import { Drawer } from "../../components/ui/Drawer";
import { ease } from "../../lib/motion";
import { copy } from "../../lib/hash";
import styles from "./Stage.module.css";
import proveStyles from "./StageProve.module.css";

export function StageProve({ flow }: { flow: StudioFlow }) {
  const verify = useVerify();
  const [busy, setBusy] = useState<"clean" | "tamper" | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [pasteResult, setPasteResult] = useState<typeof flow.verifyClean>(null);
  const [pasteBusy, setPasteBusy] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  const onClean = async () => {
    setBusy("clean");
    try {
      const r = await verify.mutateAsync(flow.generatedText);
      flow.setVerifyClean(r);
    } finally { setBusy(null); }
  };

  const onTamper = async () => {
    setBusy("tamper");
    try {
      const fake = flow.generatedText.replace(/\s/, " (FAKE!) ");
      flow.setTamperedText(fake);
      const r = await verify.mutateAsync(fake);
      flow.setVerifyTampered(r);
    } finally { setBusy(null); }
  };

  const onPasteVerify = async () => {
    if (!pasteText.trim()) return;
    setPasteBusy(true);
    try {
      const r = await verify.mutateAsync(pasteText);
      setPasteResult(r);
    } finally { setPasteBusy(false); }
  };
  const onCopySignedText = async () => {
    const ok = await copy(flow.generatedText);
    setCopyState(ok ? "copied" : "failed");
    window.setTimeout(() => setCopyState("idle"), 1800);
  };

  return (
    <div className={styles.stage}>
      <header className={styles.head}>
        <EditorialCaption number="04" rule>PROVE</EditorialCaption>
        <h2 className={styles.title}>
          Anyone can <em>verify</em> it.
        </h2>
        <p className={styles.lede}>
          The same paragraph, returned to the registry, comes back signed and
          verified. Change a single word — the proof falls apart.
        </p>
      </header>

      <div className={proveStyles.cols}>
        <ProveCard
          tone="clean"
          state={flow.verifyClean}
          busy={busy === "clean"}
          onRun={onClean}
          title="The original text"
          actionLabel={flow.verifyClean ? "Run again" : "Verify the original"}
        />
        <ProveCard
          tone="tamper"
          state={flow.verifyTampered}
          busy={busy === "tamper"}
          onRun={onTamper}
          title="A tampered copy"
          actionLabel={flow.verifyTampered ? "Tamper again" : "Try tampering"}
          tamperedSnippet={flow.tamperedText.slice(0, 90).replace(/[\u200B\u200C\u2063\u2064]/g, "")}
        />
      </div>

      {flow.bundle && (
        <ProofBundlePanel bundle={flow.bundle.proof_bundle_v2} />
      )}

      <div className={proveStyles.public}>
        <div>
          <span className={proveStyles.publicCap}>OPEN UTILITY</span>
          <h3 className={proveStyles.publicHead}>Verify any paragraph, from anywhere.</h3>
          <p className={proveStyles.publicBody}>
            Copy the signed, watermarked paragraph, paste it into a social post
            or mock page, then verify it here or with the Chrome extension.
          </p>
        </div>
        <div className={proveStyles.publicActions}>
          <MagneticButton onClick={onCopySignedText} variant="filled">
            {copyState === "copied" ? "Copied signed text" : copyState === "failed" ? "Copy failed" : "Copy signed text"}
          </MagneticButton>
          <MagneticButton onClick={() => setDrawerOpen(true)} variant="outline">
            Open the verifier
          </MagneticButton>
        </div>
      </div>

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Public verifier" side="right">
        <div className={proveStyles.drawer}>
          <p className={proveStyles.drawerLead}>
            Paste any text. We&apos;ll hash it, look it up in the public ledger,
            and report whether it carries a known Vellum signature.
          </p>
          <textarea
            className={styles.prompt}
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder="Paste a paragraph here…"
            rows={6}
          />
          <div className={proveStyles.drawerActions}>
            <MagneticButton onClick={onPasteVerify} disabled={pasteBusy || !pasteText.trim()} variant="filled">
              {pasteBusy ? "Verifying…" : "Verify"}
            </MagneticButton>
          </div>

          <AnimatePresence>
            {pasteResult && (
              <motion.div
                key={pasteResult.sha256_hash}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4, ease }}
              >
                <ResultPanel state={pasteResult} tone={pasteResult.verified ? "clean" : "tamper"} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </Drawer>
    </div>
  );
}

function ProofBundlePanel({ bundle }: { bundle: NonNullable<StudioFlow["bundle"]>["proof_bundle_v2"] }) {
  const issuer = bundle.issuer as Record<string, unknown>;
  const signature = bundle.signature as Record<string, unknown>;
  const agentAction = bundle.agent_action as Record<string, unknown> | null | undefined;
  const walletProofs = bundle.wallet_proofs ?? [];
  const anchor = (bundle.anchors?.[0] ?? {}) as Record<string, unknown>;
  const hashing = bundle.hashing as Record<string, unknown>;

  return (
    <section className={proveStyles.bundle}>
      <span className={proveStyles.publicCap}>PROOF BUNDLE</span>
      <h3 className={proveStyles.publicHead}>Identity, wallet control, and ledger receipt.</h3>
      <dl className={proveStyles.resultList}>
        <dt>Bundle</dt><dd>{bundle.bundle_id}</dd>
        <dt>Issuer</dt><dd>{String(issuer.name ?? "unknown")} #{String(issuer.issuer_id ?? "")}</dd>
        <dt>Address</dt><dd>{String(issuer.eth_address ?? "")}</dd>
        <dt>Hash</dt><dd>{String(hashing.text_hash ?? "")}</dd>
        <dt>Signature</dt><dd>{String(signature.scheme ?? "eip191_personal_sign")}</dd>
        <dt>Anchor</dt><dd>{String(anchor.type ?? "simulated_chain")} block #{String(anchor.block_num ?? "")}</dd>
        {agentAction && (
          <>
            <dt>Auth0 actor</dt>
            <dd>{String(agentAction.email ?? agentAction.subject ?? "authenticated")}</dd>
            <dt>Agent action</dt>
            <dd>{String(agentAction.action ?? "generate_watermark_sign_anchor")}</dd>
          </>
        )}
        {walletProofs.length > 0 && (
          <>
            <dt>Wallet proofs</dt>
            <dd>
              {walletProofs.map((proof, index) => (
                <span key={index} className={proveStyles.walletProof}>
                  {String(proof.wallet_type ?? "wallet")} · {String(proof.address ?? "")}
                  {proof.tx_signature ? ` · tx ${String(proof.tx_signature)}` : ""}
                </span>
              ))}
            </dd>
          </>
        )}
      </dl>
      <details className={proveStyles.raw}>
        <summary>Raw bundle JSON</summary>
        <pre>{JSON.stringify(bundle, null, 2)}</pre>
      </details>
    </section>
  );
}

function ProveCard({
  tone, title, state, busy, onRun, actionLabel, tamperedSnippet,
}: {
  tone: "clean" | "tamper";
  title: string;
  state: StudioFlow["verifyClean"];
  busy: boolean;
  onRun: () => void;
  actionLabel: string;
  tamperedSnippet?: string;
}) {
  return (
    <motion.div className={proveStyles.card} whileHover={{ y: -2 }} transition={{ duration: 0.3, ease }}>
      <span className={proveStyles.cardTitle}>{title}</span>
      <div className={proveStyles.cardBody}>
        {!state ? <span className={proveStyles.cardEmpty}>—</span>
          : <ResultPanel state={state} tone={tone} tamperedSnippet={tamperedSnippet} />}
      </div>
      <MagneticButton onClick={onRun} disabled={busy} variant={tone === "tamper" ? "outline" : "filled"} arrow={!busy}>
        {busy ? "Checking…" : actionLabel}
      </MagneticButton>
    </motion.div>
  );
}

function ResultPanel({
  state, tone, tamperedSnippet,
}: {
  state: NonNullable<StudioFlow["verifyClean"]>;
  tone: "clean" | "tamper";
  tamperedSnippet?: string;
}) {
  const ok = state.verified;
  return (
    <div className={`${proveStyles.result} ${ok ? proveStyles.ok : proveStyles.fail}`}>
      <div className={proveStyles.resultHead}>
        <span className={proveStyles.resultDot} />
        <span className={proveStyles.resultLabel}>
          {ok ? "Verified" : tone === "tamper" ? "Tamper detected" : "Not on file"}
        </span>
      </div>
      {ok ? (
        <dl className={proveStyles.resultList}>
          <dt>Signed by</dt><dd>{state.company ?? "—"}</dd>
          <dt>Issuer</dt><dd>#{state.issuer_id}</dd>
          <dt>Block</dt><dd>#{state.block_num}</dd>
          {state.timestamp && (<><dt>Anchored</dt><dd>{new Date(state.timestamp).toLocaleString()}</dd></>)}
        </dl>
      ) : (
        <div className={proveStyles.resultFail}>
          <span className={proveStyles.resultReason}>{state.reason ?? "The hash isn't in the registry."}</span>
          {tamperedSnippet && (
            <span className={proveStyles.snippet}>&ldquo;{tamperedSnippet}…&rdquo;</span>
          )}
        </div>
      )}
    </div>
  );
}
