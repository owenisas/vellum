import { useChainBlocks, useChainStatus } from "../api/chain";
import { Badge, Card } from "./ui";

function truncate(s: string | null, len = 14): string {
  if (!s) return "—";
  if (s.length <= len * 2 + 1) return s;
  return `${s.slice(0, len)}…${s.slice(-4)}`;
}

export function ChainExplorer() {
  const status = useChainStatus();
  const blocks = useChainBlocks(50, 0);

  return (
    <>
      <Card title="Chain status">
        {status.isLoading && <p className="muted">Loading…</p>}
        {status.error && (
          <p className="alert alert-error">Failed to fetch chain status.</p>
        )}
        {status.data && (
          <dl className="kv">
            <dt>Backend</dt>
            <dd>
              <Badge tone="info">{status.data.backend}</Badge>
            </dd>
            <dt>Length</dt>
            <dd>{status.data.length}</dd>
            <dt>Validity</dt>
            <dd>
              {status.data.valid ? (
                <Badge tone="success">{status.data.message}</Badge>
              ) : (
                <Badge tone="danger">{status.data.message}</Badge>
              )}
            </dd>
            {status.data.latest_block_num != null && (
              <>
                <dt>Latest block</dt>
                <dd>#{status.data.latest_block_num}</dd>
              </>
            )}
          </dl>
        )}
      </Card>

      <Card title={`Blocks (${blocks.data?.length ?? 0})`}>
        {blocks.isLoading && <p className="muted">Loading…</p>}
        {blocks.data && blocks.data.length === 0 && (
          <p className="muted">No blocks yet.</p>
        )}
        {blocks.data && blocks.data.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Timestamp</th>
                  <th>Issuer</th>
                  <th>Data hash</th>
                  <th>Tx</th>
                  <th>Solana</th>
                </tr>
              </thead>
              <tbody>
                {blocks.data.map((b) => (
                  <tr key={b.block_num}>
                    <td>#{b.block_num}</td>
                    <td className="muted">{b.timestamp}</td>
                    <td>{b.issuer_id}</td>
                    <td className="mono">{truncate(b.data_hash)}</td>
                    <td className="mono">{truncate(b.tx_hash)}</td>
                    <td>
                      {b.solana_tx_signature ? (
                        <a
                          href={`https://explorer.solana.com/tx/${b.solana_tx_signature}?cluster=devnet`}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="mono"
                        >
                          {truncate(b.solana_tx_signature, 8)}
                        </a>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
