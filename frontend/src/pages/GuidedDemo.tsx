import { useEffect, useState } from "react";
import { PageContainer } from "../layout/PageContainer";
import { Badge, Button, Card } from "../components/ui";
import { ProofBundleViewer } from "../components/ProofBundleViewer";
import { WatermarkBadge } from "../components/WatermarkBadge";
import { demoApi } from "../api/demo";
import type {
  AnchorResponse,
  DemoScenarioResponse,
  VerifyResponse,
} from "../api/types";
import { registryApi } from "../api/registry";

export function GuidedDemo() {
  const [scenario, setScenario] = useState<DemoScenarioResponse | null>(null);
  const [anchorResp, setAnchorResp] = useState<AnchorResponse | null>(null);
  const [verifyResp, setVerifyResp] = useState<VerifyResponse | null>(null);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setScenario(await demoApi.scenario());
      setStep(1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load scenario");
    } finally {
      setLoading(false);
    }
  }

  async function doAnchor() {
    if (!scenario) return;
    setError(null);
    setLoading(true);
    try {
      // The scenario endpoint already gave us a signature — so we'd need the
      // company to exist on the server first. The demo creates an ephemeral
      // company by POSTing to /api/companies with the scenario's keypair.
      const company = await fetch(
        `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5050"}/api/companies`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: scenario.company.name,
            public_key_hex: scenario.company.public_key_hex,
            eth_address: scenario.company.eth_address,
            auto_generate: false,
            admin_secret: "dev-admin-secret",
          }),
        },
      );
      const companyJson = await company.json();
      const issuer_id = companyJson.issuer_id;

      // Re-sign the SAME watermarked text to ensure we have a fresh signature
      // from the same key (ethers locally would also work; use the embedded
      // signature_hex from the scenario for simplicity).
      const resp = await fetch(
        `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5050"}/api/anchor`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: scenario.watermarked_text,
            raw_text: scenario.text,
            signature_hex: scenario.signature_hex,
            issuer_id,
            metadata: { source: "guided-demo" },
          }),
        },
      );
      if (!resp.ok) throw new Error(await resp.text());
      const data = (await resp.json()) as AnchorResponse;
      setAnchorResp(data);
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Anchor failed");
    } finally {
      setLoading(false);
    }
  }

  async function doVerify() {
    if (!scenario) return;
    setLoading(true);
    setError(null);
    try {
      setVerifyResp(await registryApi.verify(scenario.watermarked_text));
      setStep(3);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verify failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageContainer
      title="Guided demo"
      subtitle="Walk through the full Vellum pipeline with a fixture text."
    >
      {error && <div className="alert alert-error">{error}</div>}

      <Card title={`Step 1 — fixture scenario ${step >= 1 ? "✓" : ""}`}>
        {!scenario && (
          <Button onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Load demo scenario"}
          </Button>
        )}
        {scenario && (
          <>
            <p className="muted">
              The server generated a fresh keypair, fixture text, watermarked
              it, and signed it with EIP-191 personal_sign.
            </p>
            <dl className="kv">
              <dt>Company</dt>
              <dd>{scenario.company.name}</dd>
              <dt>Address</dt>
              <dd className="mono">{scenario.company.eth_address}</dd>
              <dt>Watermark</dt>
              <dd>
                <WatermarkBadge info={scenario.watermark} />
              </dd>
              <dt>SHA-256</dt>
              <dd className="mono">{scenario.sha256_hash}</dd>
            </dl>
            <pre
              className="mono"
              style={{
                background: "var(--color-panel-light)",
                padding: "12px",
                borderRadius: "6px",
                whiteSpace: "pre-wrap",
                marginTop: "10px",
              }}
            >
              {scenario.text}
            </pre>
          </>
        )}
      </Card>

      {scenario && (
        <Card title={`Step 2 — anchor ${step >= 2 ? "✓" : ""}`}>
          {!anchorResp && (
            <Button onClick={doAnchor} disabled={loading}>
              {loading ? "Anchoring…" : "Register company & anchor"}
            </Button>
          )}
          {anchorResp && (
            <>
              <Badge tone="success">
                Block #{anchorResp.chain_receipt.block_num}
              </Badge>
              <ProofBundleViewer bundle={anchorResp.proof_bundle_v2} />
            </>
          )}
        </Card>
      )}

      {anchorResp && (
        <Card title={`Step 3 — verify ${step >= 3 ? "✓" : ""}`}>
          {!verifyResp && (
            <Button onClick={doVerify} disabled={loading}>
              {loading ? "Verifying…" : "Re-verify the same text"}
            </Button>
          )}
          {verifyResp && (
            <>
              <Badge tone={verifyResp.verified ? "success" : "danger"}>
                verified={String(verifyResp.verified)}
              </Badge>
              {verifyResp.proof_bundle_v2 && (
                <ProofBundleViewer bundle={verifyResp.proof_bundle_v2} />
              )}
            </>
          )}
        </Card>
      )}
    </PageContainer>
  );
}
