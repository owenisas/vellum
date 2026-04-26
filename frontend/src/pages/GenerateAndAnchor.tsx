import { useEffect, useState } from "react";
import { ethers } from "ethers";

import { useGenerate } from "../api/chat";
import { useAnchor } from "../api/registry";
import { ModelSelector } from "../components/ModelSelector";
import { ProofBundleViewer } from "../components/ProofBundleViewer";
import { useEcdsa, sha256HexAsync } from "../hooks/useEcdsa";
import { useDemoIdentity } from "../hooks/useDemoIdentity";
import type { AnchorResponse } from "../api/types";

export function GenerateAndAnchor() {
  const { status: idStatus } = useDemoIdentity();
  const [prompt, setPrompt] = useState("Tell me about cryptographic provenance.");
  const [provider, setProvider] = useState("fixture");
  const [model, setModel] = useState("fixture");
  const [issuerId, setIssuerId] = useState(1);
  const [privateKey, setPrivateKey] = useState("");
  const [text, setText] = useState("");
  const [bundle, setBundle] = useState<AnchorResponse | null>(null);
  const [useDemoIdentityFlag, setUseDemoIdentityFlag] = useState(true);

  const generate = useGenerate();
  const anchor = useAnchor();
  const { signWithKey } = useEcdsa();

  // When demo identity is ready and user hasn't overridden, auto-fill.
  useEffect(() => {
    if (idStatus.state === "ready" && useDemoIdentityFlag) {
      setIssuerId(idStatus.identity.issuerId);
      setPrivateKey(idStatus.identity.privateKey);
    }
  }, [idStatus, useDemoIdentityFlag]);

  const handleGenerate = async () => {
    const res = await generate.mutateAsync({
      prompt,
      model,
      provider,
      watermark: true,
      watermark_params: { issuer_id: issuerId, model_id: 1, model_version_id: 1 },
    });
    setText(res.text);
  };

  const handleAnchor = async () => {
    if (!privateKey || !text) return;
    const textHash = await sha256HexAsync(text);
    const timestamp = Math.floor(Date.now() / 1000);
    const bundleNonce = "0x" + ethers.hexlify(ethers.randomBytes(32)).slice(2);
    const { signatureHex, scheme } = await signWithKey(
      {
        textHash: "0x" + textHash,
        issuerId,
        timestamp,
        bundleNonce,
      },
      privateKey,
    );
    const res = await anchor.mutateAsync({
      text,
      issuer_id: issuerId,
      signature_hex: signatureHex,
      sig_scheme: scheme,
      timestamp,
      bundle_nonce_hex: bundleNonce.slice(2),
    });
    setBundle(res);
  };

  const demoReady = idStatus.state === "ready";

  return (
    <div>
      <h2>Generate &amp; Anchor</h2>
      <p style={{ color: "var(--color-muted)" }}>
        Manual flow with full control. For the narrated walkthrough, see <a href="/demo">Live Demo</a>.
      </p>

      {demoReady && (
        <div
          className="card"
          style={{
            display: "flex",
            gap: "0.75rem",
            alignItems: "center",
            background: "rgba(79, 70, 229, 0.07)",
            borderColor: "rgba(79, 70, 229, 0.4)",
            flexWrap: "wrap",
          }}
        >
          <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input
              type="checkbox"
              checked={useDemoIdentityFlag}
              onChange={(e) => setUseDemoIdentityFlag(e.target.checked)}
            />
            Use demo identity
          </label>
          <span className="mono" style={{ fontSize: 12, color: "var(--color-muted)" }}>
            {idStatus.identity.name} · issuer #{idStatus.identity.issuerId} ·{" "}
            {idStatus.identity.address.slice(0, 10)}…{idStatus.identity.address.slice(-6)}
          </span>
        </div>
      )}

      <div className="card">
        <h3>1. Generate</h3>
        <ModelSelector
          provider={provider}
          model={model}
          onProviderChange={setProvider}
          onModelChange={setModel}
        />
        <textarea
          rows={4}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          style={{ width: "100%", marginTop: "0.5rem" }}
        />
        <div>
          <label>
            Issuer ID:{" "}
            <input
              type="number"
              value={issuerId}
              onChange={(e) => {
                setUseDemoIdentityFlag(false);
                setIssuerId(+e.target.value);
              }}
            />
          </label>
        </div>
        <button onClick={handleGenerate} disabled={generate.isPending}>
          {generate.isPending ? "Generating…" : "Generate"}
        </button>
      </div>

      {text && (
        <div className="card">
          <h3>2. Watermarked output</h3>
          <pre style={{ whiteSpace: "pre-wrap" }}>{text}</pre>
        </div>
      )}

      {text && (
        <div className="card">
          <h3>3. Sign &amp; anchor</h3>
          {useDemoIdentityFlag && demoReady ? (
            <p style={{ color: "var(--color-muted)", fontSize: 13 }}>
              Signing with the demo identity wallet. EIP-712 typed-data via ethers.js — keys never leave your browser.
            </p>
          ) : (
            <>
              <p style={{ color: "var(--color-muted)", fontSize: 13 }}>
                Paste a private key here for the demo (in production this comes from a wallet).
                EIP-712 typed-data signing.
              </p>
              <input
                type="password"
                placeholder="0x..."
                value={privateKey}
                onChange={(e) => {
                  setUseDemoIdentityFlag(false);
                  setPrivateKey(e.target.value);
                }}
                style={{ width: "100%" }}
              />
            </>
          )}
          <button onClick={handleAnchor} disabled={anchor.isPending || !privateKey}>
            {anchor.isPending ? "Anchoring…" : "Sign & Anchor"}
          </button>
        </div>
      )}

      {bundle && (
        <>
          <h3>4. Proof bundle</h3>
          {bundle.bundle_status === "pending_batch" && (
            <div className="card">
              <span className="badge warn">pending Merkle batch</span> — your bundle will be promoted within the configured window.
            </div>
          )}
          <ProofBundleViewer bundle={bundle.proof_bundle_v2} />
        </>
      )}
    </div>
  );
}
