import { useState } from "react";
import { PageContainer } from "../layout/PageContainer";
import { Badge, Button, Card } from "../components/ui";
import { ProofBundleViewer } from "../components/ProofBundleViewer";
import { WatermarkBadge } from "../components/WatermarkBadge";
import { useVerify } from "../api/registry";

export function Verify() {
  const verify = useVerify();
  const [text, setText] = useState("");

  const onVerify = async () => {
    if (!text.trim()) return;
    await verify.mutateAsync(text);
  };

  return (
    <PageContainer
      title="Verify text"
      subtitle="Paste any text — including invisible watermarks — and we'll check the registry."
    >
      <Card title="Input">
        <textarea
          className="textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste text to verify…"
          style={{ minHeight: "180px" }}
        />
        <div className="flex gap-sm mt-md">
          <Button onClick={onVerify} disabled={verify.isPending || !text.trim()}>
            {verify.isPending ? "Verifying…" : "Verify"}
          </Button>
        </div>
      </Card>

      {verify.error && (
        <div className="alert alert-error">{(verify.error as Error).message}</div>
      )}

      {verify.data && (
        <Card title="Result">
          <div className="flex gap-sm" style={{ marginBottom: "12px" }}>
            {verify.data.verified ? (
              <Badge tone="success">verified</Badge>
            ) : (
              <Badge tone="warning">not anchored</Badge>
            )}
            <WatermarkBadge info={verify.data.watermark} />
          </div>

          <dl className="kv">
            <dt>SHA-256</dt>
            <dd className="mono">{verify.data.sha256_hash}</dd>
            {verify.data.company && (
              <>
                <dt>Issuer</dt>
                <dd>
                  {verify.data.company} <span className="muted">(#{verify.data.issuer_id})</span>
                </dd>
              </>
            )}
            {verify.data.eth_address && (
              <>
                <dt>Address</dt>
                <dd className="mono">{verify.data.eth_address}</dd>
              </>
            )}
            {verify.data.block_num != null && (
              <>
                <dt>Block</dt>
                <dd>#{verify.data.block_num}</dd>
              </>
            )}
            {verify.data.timestamp && (
              <>
                <dt>Anchored at</dt>
                <dd>{verify.data.timestamp}</dd>
              </>
            )}
            {verify.data.reason && (
              <>
                <dt>Reason</dt>
                <dd>{verify.data.reason}</dd>
              </>
            )}
          </dl>

          {verify.data.proof_bundle_v2 && (
            <div className="mt-lg">
              <h3>Proof bundle</h3>
              <ProofBundleViewer bundle={verify.data.proof_bundle_v2} />
            </div>
          )}
        </Card>
      )}
    </PageContainer>
  );
}
