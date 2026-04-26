import { useChainStatus, useChainBlocks } from "../api/chain";
import { ChainExplorer } from "../components/ChainExplorer";

export function Chain() {
  const { data: status } = useChainStatus();
  const { data: blocks } = useChainBlocks(50);

  return (
    <div>
      <h2>Chain</h2>
      {status && (
        <div className="card">
          <span className="badge ok">{status.chain_type}</span>{" "}
          <span className="badge ok">{status.anchor_strategy}</span>{" "}
          <span>{status.block_count} blocks · {status.pending_batch_size} pending</span>
        </div>
      )}
      <div className="card">
        {blocks ? (
          <ChainExplorer blocks={blocks} chainType={status?.chain_type ?? "simulated"} />
        ) : (
          <div>Loading…</div>
        )}
      </div>
    </div>
  );
}
