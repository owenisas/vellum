import { useChainStatus } from "../api/chain";

export function Dashboard() {
  const { data, isLoading } = useChainStatus();
  if (isLoading) return <div>Loading…</div>;
  return (
    <div>
      <h2>Dashboard</h2>
      <div className="card">
        <h3>Chain Status</h3>
        {data && (
          <table>
            <tbody>
              <tr><td>Chain type</td><td>{data.chain_type}</td></tr>
              <tr><td>Anchor strategy</td><td>{data.anchor_strategy}</td></tr>
              <tr><td>Block count</td><td>{data.block_count}</td></tr>
              <tr><td>Latest block</td><td>{data.latest_block_num ?? "—"}</td></tr>
              <tr><td>Pending batch</td><td>{data.pending_batch_size}</td></tr>
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
