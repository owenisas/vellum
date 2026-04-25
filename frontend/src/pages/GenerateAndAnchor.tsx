import { useState } from "react";
import { PageContainer } from "../layout/PageContainer";
import { Badge, Button, Card } from "../components/ui";
import { ModelSelector } from "../components/ModelSelector";
import { ProofBundleViewer } from "../components/ProofBundleViewer";
import { useGenerate, useModels } from "../api/chat";
import { useAnchor } from "../api/registry";
import { useCompanies } from "../api/companies";
import { useEcdsa } from "../hooks/useEcdsa";
import type { AnchorResponse, ChatResponse } from "../api/types";
import { ApiError } from "../api/client";

export function GenerateAndAnchor() {
  const models = useModels();
  const generate = useGenerate();
  const anchor = useAnchor();
  const companies = useCompanies();

  const [prompt, setPrompt] = useState(
    "Write a one-paragraph explanation of how content provenance works.",
  );
  const [provider, setProvider] = useState("google");
  const [model, setModel] = useState("gemma-4-27b-it");
  const [chatResp, setChatResp] = useState<ChatResponse | null>(null);
  const [anchorResp, setAnchorResp] = useState<AnchorResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [issuerId, setIssuerId] = useState<number | "">("");
  const [privateKey, setPrivateKey] = useState("");

  const ecdsa = useEcdsa(privateKey || null);

  const onGenerate = async () => {
    setError(null);
    setChatResp(null);
    setAnchorResp(null);
    try {
      const resp = await generate.mutateAsync({
        provider,
        model,
        messages: [{ role: "user", content: prompt }],
        watermark: true,
      });
      setChatResp(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    }
  };

  const onAnchor = async () => {
    if (!chatResp) return;
    if (!issuerId) {
      setError("Pick a company / issuer ID first");
      return;
    }
    if (!privateKey) {
      setError("Paste the company's private key to sign");
      return;
    }
    setError(null);
    try {
      const { hash, signature } = await ecdsa.signText(chatResp.text);
      const resp = await anchor.mutateAsync({
        text: chatResp.text,
        raw_text: chatResp.raw_text,
        signature_hex: signature,
        issuer_id: Number(issuerId),
        metadata: { sha256: hash, provider: chatResp.provider, model: chatResp.model },
      });
      setAnchorResp(resp);
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.message}${e.errorId ? ` (${e.errorId})` : ""}`
          : e instanceof Error
            ? e.message
            : "Anchor failed";
      setError(msg);
    }
  };

  return (
    <PageContainer
      title="Generate & Anchor"
      subtitle="Run the full pipeline: generate → watermark → sign → anchor"
    >
      {error && <div className="alert alert-error">{error}</div>}

      <Card title="1. Choose a model">
        <ModelSelector
          provider={provider}
          model={model}
          onProviderChange={setProvider}
          onModelChange={setModel}
          models={models.data}
          loading={models.isLoading}
        />
      </Card>

      <Card title="2. Prompt">
        <textarea
          className="textarea"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <div className="flex gap-sm mt-md">
          <Button onClick={onGenerate} disabled={generate.isPending}>
            {generate.isPending ? "Generating…" : "Generate"}
          </Button>
        </div>
      </Card>

      {chatResp && !chatResp.error && (
        <Card title="3. Generated text">
          <div className="flex gap-sm" style={{ marginBottom: "8px" }}>
            <Badge tone="info">{chatResp.provider}</Badge>
            <Badge tone="info">{chatResp.model}</Badge>
            {chatResp.watermarked && (
              <Badge tone="success">watermarked</Badge>
            )}
            <span className="muted" style={{ fontSize: "0.85rem" }}>
              {chatResp.usage.input_tokens} in / {chatResp.usage.output_tokens} out
            </span>
          </div>
          <pre
            className="mono"
            style={{
              background: "var(--color-panel-light)",
              padding: "12px",
              borderRadius: "6px",
              whiteSpace: "pre-wrap",
            }}
          >
            {chatResp.text}
          </pre>
        </Card>
      )}

      {chatResp && (
        <Card title="4. Sign & anchor">
          <div className="row">
            <div className="col">
              <label className="label" htmlFor="issuer-select">
                Company (issuer)
              </label>
              <select
                id="issuer-select"
                className="select"
                value={issuerId}
                onChange={(e) =>
                  setIssuerId(e.target.value ? Number(e.target.value) : "")
                }
              >
                <option value="">— pick a company —</option>
                {(companies.data ?? []).map((c) => (
                  <option key={c.id} value={c.issuer_id}>
                    {c.name} (#{c.issuer_id} · {c.eth_address.slice(0, 10)}…)
                  </option>
                ))}
              </select>
            </div>
            <div className="col">
              <label className="label" htmlFor="pk-input">
                Private key (hex, never sent to server)
              </label>
              <input
                id="pk-input"
                className="input mono"
                type="password"
                value={privateKey}
                onChange={(e) => setPrivateKey(e.target.value)}
                placeholder="0x..."
              />
              {ecdsa.address && (
                <span className="muted" style={{ fontSize: "0.85rem" }}>
                  Derived address: {ecdsa.address}
                </span>
              )}
            </div>
          </div>
          <div className="mt-md">
            <Button onClick={onAnchor} disabled={anchor.isPending}>
              {anchor.isPending ? "Anchoring…" : "Sign & anchor"}
            </Button>
          </div>
        </Card>
      )}

      {anchorResp && (
        <Card title="5. Proof bundle">
          <div className="alert alert-success">
            Anchored as block #{anchorResp.chain_receipt.block_num} —{" "}
            <span className="mono">{anchorResp.chain_receipt.tx_hash.slice(0, 24)}…</span>
          </div>
          <ProofBundleViewer bundle={anchorResp.proof_bundle_v2} />
        </Card>
      )}
    </PageContainer>
  );
}
