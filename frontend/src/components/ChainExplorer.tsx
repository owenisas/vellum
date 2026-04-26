import type { ChainBlock } from "../api/chain";

interface Props {
  blocks: ChainBlock[];
  chainType: string;
}

export function ChainExplorer({ blocks, chainType }: Props) {
  return (
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Time</th>
          <th>Issuer</th>
          <th>Data hash</th>
          <th>Tx hash</th>
          {chainType === "solana" && <th>Solana</th>}
        </tr>
      </thead>
      <tbody>
        {blocks.map((b) => (
          <tr key={b.block_num}>
            <td>{b.block_num}</td>
            <td className="mono">{b.timestamp}</td>
            <td>{b.issuer_id}</td>
            <td className="mono">{b.data_hash.slice(0, 16)}…</td>
            <td className="mono">{b.tx_hash.slice(0, 16)}…</td>
            {chainType === "solana" && (
              <td>
                {b.solana_tx_signature ? (
                  <a
                    href={`https://explorer.solana.com/tx/${b.solana_tx_signature}?cluster=devnet`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    view
                  </a>
                ) : (
                  <span className="badge warn">local-only</span>
                )}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
