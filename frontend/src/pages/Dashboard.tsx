import { PageContainer } from "../layout/PageContainer";
import { Badge, Card } from "../components/ui";
import { useHealth } from "../api/registry";
import { useChainStatus } from "../api/chain";

export function Dashboard() {
  const health = useHealth();
  const status = useChainStatus();

  return (
    <PageContainer title="Dashboard" subtitle="Operational overview">
      <div className="row">
        <div className="col">
          <Card title="Service health">
            {health.isLoading && <p className="muted">Loading…</p>}
            {health.error && (
              <p className="alert alert-error">
                Unable to reach the API. Is the backend running on port 5050?
              </p>
            )}
            {health.data && (
              <dl className="kv">
                <dt>Status</dt>
                <dd>
                  <Badge tone="success">{health.data.status}</Badge>
                </dd>
                <dt>Demo mode</dt>
                <dd>
                  <Badge tone="info">{health.data.demo_mode}</Badge>
                </dd>
                <dt>Chain backend</dt>
                <dd>
                  <Badge tone="info">{health.data.chain_backend}</Badge>
                  {health.data.solana_cluster && (
                    <span className="muted"> · {health.data.solana_cluster}</span>
                  )}
                </dd>
                <dt>Auth0</dt>
                <dd>
                  {health.data.auth0_enabled ? (
                    <Badge tone="success">enabled</Badge>
                  ) : (
                    <Badge tone="warning">demo (no auth)</Badge>
                  )}
                </dd>
                <dt>Google API</dt>
                <dd>
                  {health.data.google_api_key_configured ? (
                    <Badge tone="success">configured</Badge>
                  ) : (
                    <Badge>not set</Badge>
                  )}
                </dd>
                <dt>MiniMax API</dt>
                <dd>
                  {health.data.minimax_api_key_configured ? (
                    <Badge tone="success">configured</Badge>
                  ) : (
                    <Badge>not set</Badge>
                  )}
                </dd>
              </dl>
            )}
          </Card>
        </div>

        <div className="col">
          <Card title="Chain status">
            {status.isLoading && <p className="muted">Loading…</p>}
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
        </div>
      </div>
    </PageContainer>
  );
}
