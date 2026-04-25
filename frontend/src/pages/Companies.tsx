import { useState } from "react";
import { PageContainer } from "../layout/PageContainer";
import { Badge, Button, Card } from "../components/ui";
import { useCompanies, useCreateCompany } from "../api/companies";
import type { CreateCompanyResponse } from "../api/types";
import { ApiError } from "../api/client";

export function Companies() {
  const list = useCompanies();
  const create = useCreateCompany();
  const [name, setName] = useState("");
  const [adminSecret, setAdminSecret] = useState("dev-admin-secret");
  const [created, setCreated] = useState<CreateCompanyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onCreate = async () => {
    if (!name.trim()) return;
    setError(null);
    try {
      const company = await create.mutateAsync({
        name,
        auto_generate: true,
        admin_secret: adminSecret || undefined,
      });
      setCreated(company);
      setName("");
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Create failed",
      );
    }
  };

  return (
    <PageContainer
      title="Companies"
      subtitle="Each company holds an ECDSA keypair authorized to anchor records."
    >
      <Card title="Register a company">
        {error && <div className="alert alert-error">{error}</div>}
        <label className="label" htmlFor="company-name">
          Name
        </label>
        <input
          id="company-name"
          className="input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Acme Corp"
        />
        <label className="label" htmlFor="admin-secret">
          Admin secret (only required when Auth0 is disabled)
        </label>
        <input
          id="admin-secret"
          className="input mono"
          type="password"
          value={adminSecret}
          onChange={(e) => setAdminSecret(e.target.value)}
        />
        <div className="flex gap-sm mt-md">
          <Button
            onClick={onCreate}
            disabled={create.isPending || !name.trim()}
          >
            {create.isPending ? "Creating…" : "Generate keypair & register"}
          </Button>
        </div>
      </Card>

      {created && created.private_key_hex && (
        <Card title="Save your private key">
          <div className="alert alert-success">
            We just generated a fresh secp256k1 keypair. The server only stores
            the public key — copy the private key now.
          </div>
          <dl className="kv">
            <dt>Issuer ID</dt>
            <dd>#{created.issuer_id}</dd>
            <dt>ETH address</dt>
            <dd className="mono">{created.eth_address}</dd>
            <dt>Public key</dt>
            <dd className="mono">{created.public_key_hex}</dd>
            <dt>Private key</dt>
            <dd className="mono">{created.private_key_hex}</dd>
          </dl>
          {created.note && <p className="muted mt-sm">{created.note}</p>}
        </Card>
      )}

      <Card title={`Registered (${list.data?.length ?? 0})`}>
        {list.isLoading && <p className="muted">Loading…</p>}
        {list.data && list.data.length === 0 && (
          <p className="muted">No companies yet — register one above.</p>
        )}
        {list.data && list.data.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Name</th>
                <th>Issuer ID</th>
                <th>Address</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {list.data.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>{c.name}</td>
                  <td>#{c.issuer_id}</td>
                  <td className="mono">{c.eth_address}</td>
                  <td>
                    {c.active ? (
                      <Badge tone="success">active</Badge>
                    ) : (
                      <Badge tone="warning">inactive</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </PageContainer>
  );
}
