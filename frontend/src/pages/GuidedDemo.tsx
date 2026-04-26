import { useMemo, useState } from "react";
import { ethers } from "ethers";

import { useDetect, useGenerate, useModels } from "../api/chat";
import { useAnchor, useVerify } from "../api/registry";
import { useSamplePrompts, useDemoMeta } from "../api/demo";
import { useDemoIdentity } from "../hooks/useDemoIdentity";
import { ProofBundleViewer } from "../components/ProofBundleViewer";
import type { AnchorResponse, VerifyResponse } from "../api/types";

/** Veritext EIP-712 domain & types — must match backend. */
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

async function sha256Hex(text: string): Promise<string> {
  const enc = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", enc);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Count invisible watermark tags: U+200B/U+200C/U+2063/U+2064. */
function countInvisibleChars(text: string): number {
  let n = 0;
  for (const c of text) {
    if (c === "​" || c === "‌" || c === "⁣" || c === "⁤") n++;
  }
  return n;
}

/** Render the watermarked text with invisible tags shown as a small badge for the demo. */
function VisualizedText({ text }: { text: string }) {
  const parts = useMemo(() => {
    const out: { kind: "text" | "tag"; value: string }[] = [];
    let buf = "";
    let tag = "";
    let inTag = false;
    for (const c of text) {
      const isWm = c === "​" || c === "‌" || c === "⁣" || c === "⁤";
      if (isWm) {
        if (!inTag) {
          if (buf) out.push({ kind: "text", value: buf });
          buf = "";
          inTag = true;
        }
        tag += c;
      } else {
        if (inTag) {
          out.push({ kind: "tag", value: tag });
          tag = "";
          inTag = false;
        }
        buf += c;
      }
    }
    if (buf) out.push({ kind: "text", value: buf });
    if (tag) out.push({ kind: "tag", value: tag });
    return out;
  }, [text]);

  return (
    <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.7 }}>
      {parts.map((p, i) =>
        p.kind === "text" ? (
          <span key={i}>{p.value}</span>
        ) : (
          <span
            key={i}
            title={`${p.value.length} invisible characters carrying provenance payload`}
            style={{
              display: "inline-block",
              minWidth: 18,
              height: 14,
              borderRadius: 3,
              background: "rgba(79, 70, 229, 0.35)",
              border: "1px solid rgba(79, 70, 229, 0.7)",
              verticalAlign: "middle",
              margin: "0 1px",
            }}
          />
        ),
      )}
    </div>
  );
}

type Stage = "intro" | "generated" | "anchored" | "verified";

export function GuidedDemo() {
  const { status, reset } = useDemoIdentity();
  const { data: meta } = useDemoMeta();
  const { data: modelsData } = useModels();
  const { data: prompts } = useSamplePrompts();

  const [stage, setStage] = useState<Stage>("intro");
  const [prompt, setPrompt] = useState("In one short paragraph, explain why text provenance matters for AI-generated content.");
  const [provider, setProvider] = useState<"google" | "fixture">("google");
  const [model, setModel] = useState<string>("gemma-3-12b-it");
  const [generatedText, setGeneratedText] = useState<string>("");
  const [bundle, setBundle] = useState<AnchorResponse | null>(null);

  // Tamper test
  const [tamperedText, setTamperedText] = useState<string>("");
  const [verifyResultClean, setVerifyResultClean] = useState<VerifyResponse | null>(null);
  const [verifyResultTampered, setVerifyResultTampered] = useState<VerifyResponse | null>(null);

  const generate = useGenerate();
  const anchor = useAnchor();
  const verify = useVerify();
  const detect = useDetect();

  // Default the provider/model based on what's actually available.
  useMemo(() => {
    if (!meta || !modelsData) return;
    const hasGoogle = meta.providers_available.includes("google");
    if (!hasGoogle && provider === "google") {
      setProvider("fixture");
      setModel("fixture");
    }
  }, [meta, modelsData, provider]);

  const tagCount = countInvisibleChars(generatedText);
  const visibleCount = generatedText.length - tagCount;

  if (status.state === "loading") {
    return (
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Veritext Demo</h2>
        <p>Bootstrapping a one-time demo identity in your browser…</p>
      </div>
    );
  }
  if (status.state === "error") {
    return (
      <div className="card">
        <h2>Demo unavailable</h2>
        <p>{status.error}</p>
        <p>Make sure the backend at <code>/api/demo/auto-register</code> is running.</p>
      </div>
    );
  }

  const id = status.identity;

  const handleGenerate = async () => {
    setBundle(null);
    setVerifyResultClean(null);
    setVerifyResultTampered(null);
    setTamperedText("");
    const res = await generate.mutateAsync({
      prompt,
      provider,
      model,
      watermark: true,
      watermark_params: {
        issuer_id: id.issuerId,
        model_id: 1,
        model_version_id: 1,
        key_id: 1,
      },
    });
    if (res.error) {
      throw new Error(res.error);
    }
    setGeneratedText(res.text);
    setStage("generated");
  };

  const handleAnchor = async () => {
    if (!generatedText) return;
    const textHash = await sha256Hex(generatedText);
    const timestamp = Math.floor(Date.now() / 1000);
    const nonceBytes = ethers.randomBytes(32);
    const bundleNonce = ethers.hexlify(nonceBytes);
    const sig = await id.wallet.signTypedData(DOMAIN, TYPES, {
      textHash: "0x" + textHash,
      issuerId: id.issuerId,
      timestamp,
      bundleNonce,
    });
    const res = await anchor.mutateAsync({
      text: generatedText,
      issuer_id: id.issuerId,
      signature_hex: sig,
      sig_scheme: "eip712",
      timestamp,
      bundle_nonce_hex: bundleNonce.slice(2),
    });
    setBundle(res);
    setStage("anchored");
  };

  const handleVerifyClean = async () => {
    const res = await verify.mutateAsync(generatedText);
    setVerifyResultClean(res);
    setStage("verified");
  };

  const handleVerifyTampered = async () => {
    // Build a tampered version: insert a sneaky word into the visible text.
    // We replace the first space with " (FAKE)" — preserves invisible tags but
    // changes the SHA-256.
    const fake = generatedText.replace(/\s/, " (FAKE!) ");
    setTamperedText(fake);
    const res = await verify.mutateAsync(fake);
    setVerifyResultTampered(res);
  };

  const handleStripAndDetect = async () => {
    const stripped = await detect.mutateAsync(
      generatedText.replace(/[​‌⁣⁤]/g, ""),
    );
    return stripped;
  };

  const cliCommand = bundle
    ? `veritext-verify --bundle ./bundle.json --text ./text.txt`
    : "";

  return (
    <div>
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ marginBottom: "0.25rem" }}>Live Demo</h1>
        <p style={{ color: "var(--color-muted)", marginTop: 0 }}>
          A complete provenance round-trip in 4 clicks. No wallet install, no admin keys, no setup.
        </p>
      </header>

      {/* Identity strip */}
      <div
        className="card"
        style={{
          display: "flex",
          gap: "1rem",
          alignItems: "center",
          flexWrap: "wrap",
          background: "rgba(79, 70, 229, 0.07)",
          borderColor: "rgba(79, 70, 229, 0.4)",
        }}
      >
        <span className="badge ok">Demo identity bootstrapped</span>
        <span className="mono" style={{ fontSize: 12 }}>
          {id.name} · issuer #{id.issuerId} · {id.address.slice(0, 10)}…{id.address.slice(-6)}
        </span>
        <span style={{ flex: 1 }} />
        <button onClick={reset} style={{ background: "transparent", border: "1px solid var(--color-border)" }}>
          Reset identity
        </button>
      </div>

      {/* Stage 1: Generate */}
      <Section
        n={1}
        title="Generate watermarked text"
        active={stage === "intro" || stage === "generated"}
        done={stage !== "intro"}
        explainer={
          <>
            We ask <strong>{provider === "google" ? "Gemma 3" : "the fixture provider"}</strong> for a paragraph,
            then embed an invisible 64-bit provenance tag every ~160 tokens (BCH(63,16)
            error-corrected, encoding issuer + model + version + key id).
          </>
        }
      >
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
          <select value={provider} onChange={(e) => {
            const v = e.target.value as "google" | "fixture";
            setProvider(v);
            setModel(v === "google" ? "gemma-3-12b-it" : "fixture");
          }}>
            {meta?.providers_available.includes("google") && <option value="google">Google · Gemma 3</option>}
            <option value="fixture">Fixture (deterministic)</option>
          </select>
          {provider === "google" && (
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              <option value="gemma-3-12b-it">gemma-3-12b-it</option>
              <option value="gemma-3-27b-it">gemma-3-27b-it</option>
            </select>
          )}
        </div>
        <textarea
          rows={3}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          style={{ width: "100%", marginBottom: "0.5rem" }}
        />
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "var(--color-muted)" }}>Try:</span>
          {prompts?.prompts.slice(0, 3).map((p, i) => (
            <a
              key={i}
              href="#"
              onClick={(e) => {
                e.preventDefault();
                setPrompt(p);
              }}
              style={{ fontSize: 12 }}
            >
              {p.slice(0, 40)}…
            </a>
          ))}
        </div>
        <button onClick={handleGenerate} disabled={generate.isPending}>
          {generate.isPending ? "Generating…" : stage === "intro" ? "▶ Generate" : "Generate again"}
        </button>
        {generate.isError && (
          <p style={{ color: "var(--color-error)", marginTop: "0.5rem" }}>
            {(generate.error as Error)?.message}
          </p>
        )}

        {generatedText && (
          <div style={{ marginTop: "1rem" }}>
            <div style={{ display: "flex", gap: "1rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
              <span className="badge ok">{visibleCount} visible chars</span>
              <span className="badge ok">{tagCount} invisible watermark chars</span>
              <span className="badge ok">{Math.ceil(tagCount / 67)} provenance tags</span>
            </div>
            <div
              style={{
                padding: "0.75rem",
                background: "var(--color-bg)",
                borderRadius: "var(--radius)",
                border: "1px solid var(--color-border)",
              }}
            >
              <VisualizedText text={generatedText} />
            </div>
            <p style={{ fontSize: 12, color: "var(--color-muted)", marginTop: "0.5rem" }}>
              The purple boxes are invisible Unicode (U+200B/200C/2063/2064). Copy-paste this text anywhere — the tags travel with it.
            </p>
          </div>
        )}
      </Section>

      {/* Stage 2: Sign + Anchor */}
      {generatedText && (
        <Section
          n={2}
          title="Sign with EIP-712 + anchor on chain"
          active={stage === "generated" || stage === "anchored"}
          done={stage === "anchored" || stage === "verified"}
          explainer={
            <>
              Your browser hashes the text (SHA-256), signs the {`{ textHash, issuerId, timestamp, bundleNonce }`} struct
              with EIP-712 typed data using the demo wallet, and POSTs to <code>/api/anchor</code>.
              The backend recovers the signer, verifies it matches issuer #{id.issuerId},
              and writes a block to the {meta?.chain_backend === "solana" ? "Solana devnet" : "simulated"} chain.
            </>
          }
        >
          <button onClick={handleAnchor} disabled={anchor.isPending || !generatedText}>
            {anchor.isPending ? "Signing & anchoring…" : bundle ? "Re-anchor" : "▶ Sign & Anchor"}
          </button>
          {anchor.isError && (
            <p style={{ color: "var(--color-error)", marginTop: "0.5rem" }}>
              {(anchor.error as Error)?.message}
            </p>
          )}
          {bundle && (
            <div style={{ marginTop: "1rem" }}>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <span className="badge ok">scheme: {bundle.proof_bundle_v2.signature.scheme}</span>
                <span className="badge ok">canon: {bundle.proof_bundle_v2.signature.canonicalization}</span>
                <span className="badge ok">block #{bundle.chain_receipt.block_num}</span>
                <span className="badge ok">{bundle.bundle_status}</span>
              </div>
              <div className="mono" style={{ fontSize: 12, marginTop: "0.5rem" }}>
                bundle_id: {bundle.proof_bundle_v2.bundle_id}
              </div>
              <div className="mono" style={{ fontSize: 12 }}>
                tx_hash:&nbsp;&nbsp;&nbsp;{bundle.chain_receipt.tx_hash}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* Stage 3: Verify + tamper test */}
      {bundle && (
        <Section
          n={3}
          title="Verify — clean text passes, tampered text fails"
          active={stage === "anchored" || stage === "verified"}
          done={stage === "verified"}
          explainer={
            <>
              Anyone can call <code>POST /api/verify</code> with the text. The server hashes it,
              looks up the chain block by hash, and reports whether the recorded issuer matches.
              We also run a tamper test by inserting <code>"(FAKE!)"</code> into the visible text —
              the SHA-256 changes, so the lookup fails.
            </>
          }
        >
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button onClick={handleVerifyClean} disabled={verify.isPending}>
              ✓ Verify clean text
            </button>
            <button
              onClick={handleVerifyTampered}
              disabled={verify.isPending}
              style={{ background: "var(--color-error)" }}
            >
              ✗ Try tampering
            </button>
          </div>

          {verifyResultClean && (
            <div className="card" style={{ marginTop: "1rem", marginBottom: 0 }}>
              <strong style={{ color: verifyResultClean.verified ? "var(--color-success)" : "var(--color-error)" }}>
                {verifyResultClean.verified ? "✓ VERIFIED" : "✗ NOT FOUND"}
              </strong>
              {verifyResultClean.verified && (
                <div className="mono" style={{ fontSize: 12, marginTop: "0.5rem" }}>
                  <div>company: {verifyResultClean.company}</div>
                  <div>issuer_id: {verifyResultClean.issuer_id}</div>
                  <div>eth_address: {verifyResultClean.eth_address}</div>
                  <div>block #{verifyResultClean.block_num} @ {verifyResultClean.timestamp}</div>
                </div>
              )}
            </div>
          )}

          {verifyResultTampered && (
            <div className="card" style={{ marginTop: "1rem", marginBottom: 0 }}>
              <strong style={{ color: verifyResultTampered.verified ? "var(--color-success)" : "var(--color-error)" }}>
                {verifyResultTampered.verified ? "✓ VERIFIED (unexpected!)" : "✗ NOT FOUND — tamper detected"}
              </strong>
              <div className="mono" style={{ fontSize: 12, marginTop: "0.5rem" }}>
                tampered hash: {verifyResultTampered.sha256_hash.slice(0, 32)}…
              </div>
              <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: "0.5rem" }}>
                Tampered text:{" "}
                <em>{tamperedText.slice(0, 80).replace(/[​‌⁣⁤]/g, "")}…</em>
              </div>
            </div>
          )}
        </Section>
      )}

      {/* Stage 4: Inspect */}
      {bundle && (
        <Section
          n={4}
          title="Inspect the proof bundle (or verify offline)"
          active={true}
          done={true}
          explainer={
            <>
              The full bundle is an RFC 8785-canonicalized JSON, signed end-to-end. You can verify
              it offline with the <code>veritext-verify</code> CLI (no server required).
            </>
          }
        >
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
            <button onClick={() => downloadJson("bundle.json", bundle.proof_bundle_v2)}>
              ⬇ Download bundle.json
            </button>
            <button
              onClick={() => downloadText("text.txt", generatedText)}
              style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
            >
              ⬇ Download text.txt
            </button>
            <button
              onClick={() => navigator.clipboard.writeText(cliCommand)}
              style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
            >
              ⧉ Copy CLI command
            </button>
          </div>
          <pre style={{ fontSize: 12, marginTop: 0 }}>
            <code>{cliCommand}</code>
          </pre>
          <ProofBundleViewer bundle={bundle.proof_bundle_v2} />
        </Section>
      )}
    </div>
  );
}

function Section({
  n,
  title,
  active,
  done,
  explainer,
  children,
}: {
  n: number;
  title: string;
  active: boolean;
  done: boolean;
  explainer: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div
      className="card"
      style={{
        opacity: active ? 1 : 0.5,
        borderColor: done ? "var(--color-success)" : "var(--color-border)",
        position: "relative",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
        <span
          className="badge"
          style={{
            background: done ? "var(--color-success)" : "var(--color-primary)",
            color: "#fff",
            minWidth: 24,
            textAlign: "center",
          }}
        >
          {done ? "✓" : n}
        </span>
        <h3 style={{ margin: 0 }}>{title}</h3>
      </div>
      <p style={{ color: "var(--color-muted)", fontSize: 13, marginTop: 0 }}>{explainer}</p>
      {children}
    </div>
  );
}

function downloadJson(filename: string, obj: unknown) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
  triggerDownload(filename, blob);
}
function downloadText(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/plain" });
  triggerDownload(filename, blob);
}
function triggerDownload(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
