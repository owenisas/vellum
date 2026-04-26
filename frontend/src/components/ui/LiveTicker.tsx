import { useChainBlocks, useChainStatus } from "../../api/chain";
import { cn } from "../../lib/cn";
import styles from "./LiveTicker.module.css";

type Props = { className?: string; verbose?: boolean };

function formatRelative(iso: string | undefined): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (isNaN(t)) return "—";
  const delta = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (delta < 60) return `${delta}s ago`;
  if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.floor(delta / 3600)}h ago`;
  return `${Math.floor(delta / 86400)}d ago`;
}

export function LiveTicker({ className, verbose = false }: Props) {
  const { data: status, isLoading } = useChainStatus();
  const { data: blocks } = useChainBlocks(1);
  const count = status?.block_count ?? 0;
  const chain = status?.chain_type ?? "—";
  const last = blocks?.[0]?.timestamp;
  return (
    <div className={cn(styles.row, className)}>
      <span className={styles.dot} aria-hidden />
      <span className={styles.label}>Live</span>
      <span className={styles.value}>
        {isLoading
          ? "syncing…"
          : verbose
          ? `${count.toLocaleString()} sentences anchored on ${chain} · last ${formatRelative(last)}`
          : `${count.toLocaleString()} ANCHORED · ${chain.toUpperCase()}`}
      </span>
    </div>
  );
}
