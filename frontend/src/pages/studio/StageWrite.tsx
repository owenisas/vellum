import { useMemo, useState } from "react";
import { motion } from "framer-motion";

import type { StudioFlow } from "./StudioState";
import { useGenerate, useModels } from "../../api/chat";
import { Pill } from "../../components/ui/Pill";
import { MagneticButton } from "../../components/ui/MagneticButton";
import { EditorialCaption } from "../../components/ui/EditorialCaption";
import { VisualizedText } from "./VisualizedText";
import { ease } from "../../lib/motion";
import styles from "./Stage.module.css";

const INVISIBLE = /[\u200B\u200C\u2063\u2064]/g;
async function sha256Hex(text: string): Promise<string> {
  const enc = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", enc);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

const SAMPLE_PROMPTS = [
  "Write a one-paragraph explanation of how content provenance works.",
  "Explain why authenticated AI agent actions matter for regulated teams.",
  "Describe how browser wallets can prove provenance without sharing private keys.",
];

export function StageWrite({ flow }: { flow: StudioFlow }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const generate = useGenerate();
  const models = useModels();

  const tagCount = (flow.generatedText.match(INVISIBLE) || []).length;
  const visibleCount = flow.generatedText.length - tagCount;
  const tagGroups = Math.ceil(tagCount / 67) || 0;
  const providerModels = useMemo(() => {
    const data = models.data;
    return {
      google: data?.google ?? [],
      fixture: [{ id: "fixture", name: "Fixture", provider: "fixture" }],
    };
  }, [models.data]);
  const providers = [
    ...(providerModels.google.length ? ["google" as const] : []),
    "fixture" as const,
  ];

  const onGenerate = async () => {
    setBusy(true);
    setErr(null);
    flow.setBundle(null);
    flow.setVerifyClean(null);
    flow.setVerifyTampered(null);
    flow.setTamperedText("");
    flow.setSignature("");
    flow.setTextHash("");
    flow.setRawText("");
    flow.setWalletProofs([]);
    try {
      const res = await generate.mutateAsync({
        provider: flow.provider,
        model: flow.provider === "fixture" ? undefined : flow.model,
        messages: [{ role: "user", content: flow.prompt }],
        watermark: true,
        wm_params: flow.issuerId
          ? { issuer_id: Number(flow.issuerId), model_id: 1, model_version_id: 1, key_id: 1 }
          : undefined,
      });
      if (res.error) throw new Error(res.error);
      flow.setGeneratedText(res.text);
      flow.setRawText(res.raw_text);
      const h = await sha256Hex(res.text);
      flow.setTextHash(h);
      // Defer so #stage-sign mounts, then follow the demo to Sign (matches Gemini / Write flow)
      window.setTimeout(() => flow.setStage("sign"), 220);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.stage}>
      <header className={styles.head}>
        <EditorialCaption number="01" rule>WRITE</EditorialCaption>
        <h2 className={styles.title}>
          Begin with <em>a sentence</em>.
        </h2>
        <p className={styles.lede}>
          Type a prompt. The model will write a paragraph and embed an invisible
          provenance tag — every ~160 tokens — that travels with the text.
        </p>
      </header>

      <div className={styles.body}>
        <div className={styles.controls}>
          <div className={styles.row}>
            <span className={styles.rowLabel}>Provider</span>
            <div className={styles.pills}>
              {providers.includes("google") && (
                <Pill
                  active={flow.provider === "google"}
                  onClick={() => {
                    flow.setProvider("google");
                    flow.setModel(providerModels.google[0]?.id ?? "gemma-4-27b-it");
                  }}
                >Google · Gemma</Pill>
              )}
              <Pill
                active={flow.provider === "fixture"}
                onClick={() => { flow.setProvider("fixture"); flow.setModel("fixture"); }}
              >Fixture</Pill>
            </div>
          </div>

          {flow.provider === "google" && (
            <div className={styles.row}>
              <span className={styles.rowLabel}>Model</span>
              <div className={styles.pills}>
                {providerModels.google.map((m) => (
                  <Pill key={m.id} active={flow.model === m.id} onClick={() => flow.setModel(m.id)}>
                    {m.name || m.id}
                  </Pill>
                ))}
              </div>
            </div>
          )}
        </div>

        <textarea
          className={styles.prompt}
          rows={3}
          value={flow.prompt}
          onChange={(e) => flow.setPrompt(e.target.value)}
          placeholder="Tell us what you want to make…"
        />

        <div className={styles.suggestions}>
          <span className={styles.rowLabel}>Try one</span>
          <div className={styles.suggestList}>
            {SAMPLE_PROMPTS.map((p, i) => (
              <button
                key={i}
                type="button"
                className={styles.suggestion}
                onClick={() => flow.setPrompt(p)}
              >&ldquo;{p.slice(0, 110)}{p.length > 110 ? "…" : ""}&rdquo;</button>
            ))}
          </div>
        </div>

        <div className={styles.actions}>
          <MagneticButton onClick={onGenerate} disabled={busy || !flow.prompt.trim()}>
            {busy ? "Writing…" : flow.generatedText ? "Write again" : "Write the paragraph"}
          </MagneticButton>
          {err && <span className={styles.err}>{err}</span>}
        </div>

        {flow.generatedText && (
          <motion.div
            className={styles.output}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease }}
          >
            <div className={styles.metrics}>
              <Metric label="characters" value={visibleCount.toLocaleString()} />
              <Metric label="invisible" value={tagCount.toString()} accent />
              <Metric label="tags" value={tagGroups.toString()} accent />
              <Metric label="model" value={flow.model} />
            </div>
            <div className={styles.outputBox}>
              <VisualizedText text={flow.generatedText} />
            </div>
            <p className={styles.foot}>
              The faint vertical shimmers are zero-width Unicode characters carrying
              your signature. Copy this text anywhere — they travel with it.
            </p>
            <div className={styles.next}>
              <MagneticButton onClick={() => flow.setStage("sign")} variant="filled">
                Continue to sign
              </MagneticButton>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={styles.metric}>
      <span className={styles.metricLabel}>{label}</span>
      <span className={`${styles.metricValue} ${accent ? styles.accent : ""}`}>{value}</span>
    </div>
  );
}
