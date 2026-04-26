import { useProofBundle } from "../hooks/useProofBundle";
import type { ProofBundleV2 } from "../api/types";
import { WatermarkBadge } from "./WatermarkBadge";

interface Props {
  bundle: ProofBundleV2;
  showRawJson?: boolean;
}

export function ProofBundleViewer({ bundle, showRawJson = true }: Props) {
  const { explorerUrl, chainType, inclusionProof, merkleRoot, bundleId } = useProofBundle(bundle);

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Proof Bundle <span className="mono">{bundleId}</span></h3>
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <WatermarkBadge
          detected={bundle.watermark.detected}
          tagCount={bundle.watermark.tag_count}
          validCount={bundle.watermark.valid_count}
        />
        <span className="badge ok">scheme: {bundle.signature.scheme}</span>
        <span className="badge ok">canon: {bundle.signature.canonicalization}</span>
        {bundle.encrypted_payload_metadata && (
          <span className="badge warn">encrypted ({bundle.encrypted_payload_metadata.algorithm})</span>
        )}
        {bundle.watermark.generation_time?.present && (
          <span className="badge ok">SynthID p={bundle.watermark.generation_time.p_value.toFixed(3)}</span>
        )}
      </div>

      <div className="mono" style={{ fontSize: 12, marginBottom: "1rem" }}>
        <div>Issuer: {bundle.issuer.name} (#{bundle.issuer.issuer_id}, key #{bundle.issuer.current_key_id})</div>
        <div>Address: {bundle.issuer.eth_address}</div>
        <div>Text hash: {bundle.hashing.text_hash.slice(0, 32)}…</div>
        <div>Signed fields: {bundle.signed_fields.join(", ")}</div>
      </div>

      {bundle.anchors.map((a, i) => (
        <div key={i} className="mono" style={{ marginBottom: "0.5rem" }}>
          <div>Anchor: <strong>{a.type}</strong> at {a.timestamp}</div>
          {a.tx_hash && <div>tx: {a.tx_hash.slice(0, 32)}…</div>}
          {merkleRoot && <div>merkle root: {merkleRoot.slice(0, 32)}…</div>}
          {inclusionProof && inclusionProof.length > 0 && (
            <div>inclusion proof: {inclusionProof.length} steps</div>
          )}
          {explorerUrl && (
            <div>
              <a href={explorerUrl} target="_blank" rel="noopener noreferrer">
                View on Solana Explorer →
              </a>
            </div>
          )}
        </div>
      ))}
      <div className="mono" style={{ fontSize: 12, color: "var(--color-muted)" }}>
        Verification: {chainType}
      </div>
      {showRawJson && (
        <details style={{ marginTop: "1rem" }}>
          <summary>Raw JSON</summary>
          <pre>{JSON.stringify(bundle, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}
