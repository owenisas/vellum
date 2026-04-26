import { useState } from "react";
import { ethers } from "ethers";

import { useCompanies, useCreateCompany, useRotateKey } from "../api/companies";
import { useDemoMeta } from "../api/demo";

export function Companies() {
  const { data, refetch } = useCompanies();
  const { data: meta } = useDemoMeta();
  const create = useCreateCompany();
  const [name, setName] = useState("");
  const [issuerId, setIssuerId] = useState(1);
  const [adminSecret, setAdminSecret] = useState("");
  const [pkey, setPkey] = useState("");

  const demoMode = meta?.demo_mode === "live";

  const handleCreate = async () => {
    const wallet = pkey ? new ethers.Wallet(pkey) : ethers.Wallet.createRandom();
    await create.mutateAsync({
      name,
      issuer_id: issuerId,
      eth_address: wallet.address,
      public_key_hex: wallet.address,
      // demo mode: server ignores admin_secret; field is optional
      admin_secret: adminSecret || undefined,
    });
    refetch();
  };

  return (
    <div>
      <h2>Companies</h2>
      {demoMode && (
        <p style={{ color: "var(--color-muted)", fontSize: 13 }}>
          Demo mode: registration does not require an admin secret. New issuers are limited to
          the local server's database.
        </p>
      )}
      <div className="card">
        <h3>Register</h3>
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <input type="number" placeholder="Issuer ID" value={issuerId} onChange={(e) => setIssuerId(+e.target.value)} />
        {!demoMode && (
          <input
            placeholder="Admin secret"
            value={adminSecret}
            onChange={(e) => setAdminSecret(e.target.value)}
          />
        )}
        <input placeholder="Private key (optional, generates if empty)" value={pkey} onChange={(e) => setPkey(e.target.value)} />
        <button onClick={handleCreate} disabled={create.isPending}>Register</button>
      </div>
      <div className="card">
        <h3>Registered</h3>
        <table>
          <thead><tr><th>Issuer</th><th>Name</th><th>Address</th><th>Key #</th><th>Created</th></tr></thead>
          <tbody>
            {data?.map((c) => (
              <tr key={c.issuer_id}>
                <td>{c.issuer_id}</td>
                <td>{c.name}</td>
                <td className="mono">{c.eth_address}</td>
                <td>{c.current_key_id}</td>
                <td>{c.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data?.[0] && <RotateForm issuerId={data[0].issuer_id} onDone={refetch} />}
    </div>
  );
}

function RotateForm({ issuerId, onDone }: { issuerId: number; onDone: () => void }) {
  const rotate = useRotateKey(issuerId);
  const [grace, setGrace] = useState(7);
  const handle = async () => {
    const w = ethers.Wallet.createRandom();
    await rotate.mutateAsync({
      new_eth_address: w.address,
      new_public_key_hex: w.address,
      grace_period_days: grace,
    });
    onDone();
  };
  return (
    <div className="card">
      <h3>Rotate Key (issuer {issuerId})</h3>
      <input type="number" value={grace} onChange={(e) => setGrace(+e.target.value)} placeholder="Grace days" />
      <button onClick={handle} disabled={rotate.isPending}>Rotate</button>
    </div>
  );
}
