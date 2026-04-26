import { useMemo, useState } from "react";
import type { ProofBundleV2 } from "../api/types";
import { Badge, Button } from "./ui";

export function ProofBundleViewer({ bundle }: { bundle: ProofBundleV2 }) {
  const [copied, setCopied] = useState(false);
  const json = useMemo(() => JSON.stringify(bundle, null, 2), [bundle]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(json);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard not available */
    }
  };

  const issuer = bundle.issuer as Record<string, unknown>;
  const agentAction = bundle.agent_action as Record<string, unknown> | null | undefined;
  const sig = bundle.signature as Record<string, unknown>;
  const watermark = bundle.watermark as Record<string, unknown>;
  const anchor = (bundle.anchors?.[0] ?? {}) as Record<string, unknown>;
  const hints = bundle.verification_hints as Record<string, unknown>;
  const explorer = hints?.explorer_url as string | undefined;
  const chainType = hints?.chain_type as string | undefined;

  return (
    <div>
      <div className="flex-between mt-sm" style={{ marginBottom: "12px" }}>
        <div className="flex gap-sm">
          <Badge tone="info">{bundle.spec}</Badge>
          {chainType && <Badge tone="success">chain: {chainType}</Badge>}
        </div>
        <Button variant="secondary" onClick={copy}>
          {copied ? "Copied!" : "Copy JSON"}
        </Button>
      </div>

      <dl className="kv">
        <dt>Bundle ID</dt>
        <dd className="mono">{bundle.bundle_id}</dd>
        <dt>Issuer</dt>
        <dd>
          {String(issuer?.name ?? "")}{" "}
          <span className="muted">(#{String(issuer?.issuer_id ?? "")})</span>
        </dd>
        <dt>Address</dt>
        <dd className="mono">{String(issuer?.eth_address ?? "")}</dd>
        {agentAction && (
          <>
            <dt>Auth0 actor</dt>
            <dd>
              <span className="mono">{String(agentAction.subject ?? "")}</span>
              {agentAction.email && (
                <span className="muted"> ({String(agentAction.email)})</span>
              )}
            </dd>
            <dt>Agent action</dt>
            <dd>
              <Badge tone="success">{String(agentAction.action ?? "secured")}</Badge>
              {agentAction.model && (
                <span className="muted"> via {String(agentAction.model)}</span>
              )}
            </dd>
          </>
        )}
        <dt>Signature</dt>
        <dd className="mono">{String(sig?.signature_hex ?? "")}</dd>
        <dt>Text hash</dt>
        <dd className="mono">{String((bundle.hashing as any)?.text_hash ?? "")}</dd>
        <dt>Watermark</dt>
        <dd>
          {watermark?.detected ? (
            <Badge tone="success">
              {String(watermark?.valid_count)} valid /{" "}
              {String(watermark?.tag_count)} total
            </Badge>
          ) : (
            <Badge tone="warning">Not detected</Badge>
          )}
        </dd>
        <dt>Anchor</dt>
        <dd>
          <Badge tone="info">{String(anchor?.type ?? "")}</Badge>{" "}
          <span className="mono muted">block #{String(anchor?.block_num ?? "")}</span>
        </dd>
        {explorer && (
          <>
            <dt>Explorer</dt>
            <dd>
              <a href={explorer} target="_blank" rel="noreferrer noopener">
                {explorer}
              </a>
            </dd>
          </>
        )}
      </dl>

      <details style={{ marginTop: "16px" }}>
        <summary className="muted" style={{ cursor: "pointer" }}>
          Raw bundle JSON
        </summary>
        <pre
          className="mono"
          style={{
            background: "var(--color-panel-light)",
            padding: "12px",
            borderRadius: "6px",
            overflow: "auto",
            maxHeight: "400px",
          }}
        >
          {json}
        </pre>
      </details>
    </div>
  );
}
