import { useState } from "react";
import { copy, shortAddress } from "../../lib/hash";
import { cn } from "../../lib/cn";
import styles from "./AddressBlock.module.css";

type Props = { address: string; label?: string; className?: string; full?: boolean; };

export function AddressBlock({ address, label, className, full = false }: Props) {
  const [copied, setCopied] = useState(false);
  const display = full ? address : shortAddress(address, 8, 6);
  const handle = async () => {
    if (await copy(address)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1100);
    }
  };
  return (
    <button type="button" className={cn(styles.btn, className)} onClick={handle} title={address}>
      {label && <span className={styles.label}>{label}</span>}
      <span className={styles.addr}>{display}</span>
      <span className={cn(styles.copy, copied && styles.copied)}>{copied ? "✓" : "⌘"}</span>
    </button>
  );
}
