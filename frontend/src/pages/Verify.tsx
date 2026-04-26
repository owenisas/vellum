import { useState } from "react";
import { useVerify } from "../api/registry";
import { WatermarkBadge } from "../components/WatermarkBadge";

export function Verify() {
  const [text, setText] = useState("");
  const verify = useVerify();
  const handleVerify = () => verify.mutate(text);

  return (
    <div>
      <h2>Verify</h2>
      <div className="card">
        <p>Paste any text to check whether it was emitted by a registered Veritext issuer.</p>
        <textarea rows={6} style={{ width: "100%" }} value={text} onChange={(e) => setText(e.target.value)} />
        <button onClick={handleVerify} disabled={verify.isPending || !text}>
          {verify.isPending ? "Verifying…" : "Verify"}
        </button>
      </div>
      {verify.data && (
        <div className="card">
          <h3>Result</h3>
          <p>
            <WatermarkBadge
              detected={verify.data.watermark.unicode.detected}
              tagCount={verify.data.watermark.unicode.tag_count}
            />
            {" "}
            <span className={"badge " + (verify.data.verified ? "ok" : "warn")}>
              {verify.data.verified ? "✓ verified in registry" : "✗ not in registry"}
            </span>
          </p>
          {verify.data.verified && (
            <table>
              <tbody>
                <tr><td>Issuer</td><td>{verify.data.company} (#{verify.data.issuer_id})</td></tr>
                <tr><td>Address</td><td className="mono">{verify.data.eth_address}</td></tr>
                <tr><td>Block</td><td>{verify.data.block_num}</td></tr>
                <tr><td>Timestamp</td><td>{verify.data.timestamp}</td></tr>
              </tbody>
            </table>
          )}
          {verify.data.reason && <p style={{ color: "var(--color-muted)" }}>{verify.data.reason}</p>}
        </div>
      )}
    </div>
  );
}
