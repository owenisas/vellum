import { useState } from "react";
import { ethers } from "ethers";

import { useCreateCompany, useRotateKey, useCompanies } from "../../api/companies";
import { useDemoMeta } from "../../api/demo";
import { Drawer } from "../../components/ui/Drawer";
import { Button } from "../../components/ui/Button";
import { AddressBlock } from "../../components/ui/AddressBlock";
import styles from "./AdminDrawer.module.css";

type Props = { open: boolean; onClose: () => void; };

export function AdminDrawer({ open, onClose }: Props) {
  return (
    <Drawer open={open} onClose={onClose} title="Issuer administration" side="right">
      <div className={styles.body}>
        <p className={styles.lede}>
          Register a new issuer or rotate an issuer&apos;s ECDSA key. Reserved
          for operators with the registry admin secret.
        </p>
        <CreateForm />
        <RotateForm />
      </div>
    </Drawer>
  );
}

function CreateForm() {
  const create = useCreateCompany();
  const { data: meta } = useDemoMeta();
  const [name, setName] = useState("");
  const [issuerId, setIssuerId] = useState("");
  const [pkey, setPkey] = useState("");
  const [adminSecret, setAdminSecret] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    setErr(null); setResult(null);
    try {
      let pk = pkey;
      if (!pk) {
        pk = ethers.Wallet.createRandom().privateKey;
        setPkey(pk);
      }
      const wallet = new ethers.Wallet(pk);
      const created = await create.mutateAsync({
        name,
        issuer_id: parseInt(issuerId, 10),
        eth_address: wallet.address,
        public_key_hex: wallet.signingKey.publicKey,
        admin_secret: adminSecret || undefined,
      });
      setResult(`Registered ${created.name} as issuer #${created.issuer_id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <section className={styles.section}>
      <h3 className={styles.h}>Register new issuer</h3>
      <div className={styles.grid}>
        <Field label="Display name" value={name} onChange={setName} placeholder="Acme Studios" />
        <Field label="Issuer ID" value={issuerId} onChange={setIssuerId} placeholder="42" />
        <Field label="Private key (optional)" value={pkey} onChange={setPkey} placeholder="0x… (auto-generated if blank)" mono />
        {meta?.demo_mode === "fixture" && (
          <Field label="Admin secret" value={adminSecret} onChange={setAdminSecret} placeholder="…" mono />
        )}
      </div>
      <div className={styles.actions}>
        <Button onClick={submit} disabled={create.isPending || !name || !issuerId}>
          {create.isPending ? "Registering…" : "Register"}
        </Button>
      </div>
      {pkey && <AddressBlock address={new ethers.Wallet(pkey).address} label="Generated address" />}
      {result && <p className={styles.ok}>{result}</p>}
      {err && <p className={styles.err}>{err}</p>}
    </section>
  );
}

function RotateForm() {
  const { data: companies } = useCompanies();
  const [issuerId, setIssuerId] = useState<number | null>(null);
  const [grace, setGrace] = useState("7");
  const [result, setResult] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const rotate = useRotateKey(issuerId ?? 0);

  const submit = async () => {
    if (issuerId === null) return;
    setErr(null); setResult(null);
    try {
      const w = ethers.Wallet.createRandom();
      const r = await rotate.mutateAsync({
        new_eth_address: w.address,
        new_public_key_hex: w.signingKey.publicKey,
        grace_period_days: parseInt(grace, 10),
      });
      setResult(`Rotated to key #${r.new_key_id}, prior key valid until ${r.grace_until}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <section className={styles.section}>
      <h3 className={styles.h}>Rotate issuer key</h3>
      <div className={styles.grid}>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Issuer</span>
          <select
            value={issuerId ?? ""}
            onChange={(e) => setIssuerId(e.target.value ? parseInt(e.target.value, 10) : null)}
          >
            <option value="">Select…</option>
            {(companies ?? []).map((c) => (
              <option key={c.issuer_id} value={c.issuer_id}>
                {c.name} (#{c.issuer_id})
              </option>
            ))}
          </select>
        </div>
        <Field label="Grace period (days)" value={grace} onChange={setGrace} mono />
      </div>
      <div className={styles.actions}>
        <Button onClick={submit} disabled={rotate.isPending || issuerId === null}>
          {rotate.isPending ? "Rotating…" : "Rotate key"}
        </Button>
      </div>
      {result && <p className={styles.ok}>{result}</p>}
      {err && <p className={styles.err}>{err}</p>}
    </section>
  );
}

function Field({
  label, value, onChange, placeholder, mono,
}: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; mono?: boolean; }) {
  return (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={mono ? styles.mono : ""}
      />
    </label>
  );
}
