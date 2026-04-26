import { useState } from "react";
import { copy, splitHash } from "../../lib/hash";
import { cn } from "../../lib/cn";
import styles from "./HashBlock.module.css";

type Props = { hex: string; group?: number; label?: string; className?: string; compact?: boolean; };

export function HashBlock({ hex, group = 8, label, className, compact }: Props) {
  const [copied, setCopied] = useState(false);
  const groups = splitHash(hex || "", group);
  const handle = async () => {
    if (!hex) return;
    if (await copy(hex)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1100);
    }
  };
  return (
    <div className={cn(styles.wrap, compact && styles.compact, className)}>
      {label && <span className={styles.label}>{label}</span>}
      <button type="button" className={styles.row} onClick={handle} title="click to copy">
        {groups.map((g, i) => (
          <span key={i} className={styles.group}>{g}</span>
        ))}
        <span className={cn(styles.copy, copied && styles.copied)}>{copied ? "copied" : "copy"}</span>
      </button>
    </div>
  );
}
