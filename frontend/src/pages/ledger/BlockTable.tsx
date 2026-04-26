import { motion } from "framer-motion";
import type { ChainBlock } from "../../api/chain";
import { shortAddress } from "../../lib/hash";
import { ease } from "../../lib/motion";
import styles from "./BlockTable.module.css";

type Props = {
  blocks: ChainBlock[];
  hoverIndex?: number | null;
  setHoverIndex?: (i: number | null) => void;
  chainType?: string;
};

export function BlockTable({ blocks, hoverIndex, setHoverIndex, chainType }: Props) {
  return (
    <div className={styles.wrap}>
      <header className={styles.head}>
        <span>№</span>
        <span>Anchored</span>
        <span>Issuer</span>
        <span>Hash</span>
        <span>Tx</span>
      </header>
      <ol className={styles.list}>
        {blocks.map((b, i) => {
          const onSolana = !!b.solana_tx_signature;
          return (
            <motion.li
              key={`${b.block_num}-${b.tx_hash}`}
              className={`${styles.row} ${hoverIndex === i ? styles.rowHover : ""}`}
              onMouseEnter={() => setHoverIndex?.(i)}
              onMouseLeave={() => setHoverIndex?.(null)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease, delay: i * 0.012 }}
            >
              <span className={styles.num}>{String(b.block_num).padStart(4, "0")}</span>
              <span className={styles.time} title={b.timestamp}>{timeAgo(b.timestamp)}</span>
              <span className={styles.issuer}>#{b.issuer_id}</span>
              <span className={styles.hash}>{shortAddress(b.data_hash, 10, 6)}</span>
              <span className={styles.tx}>
                {onSolana && chainType === "solana" ? (
                  <a
                    href={`https://explorer.solana.com/tx/${b.solana_tx_signature}?cluster=devnet`}
                    target="_blank"
                    rel="noreferrer noopener"
                    className={`${styles.txLink} link-u`}
                  >{shortAddress(b.solana_tx_signature ?? "", 6, 4)} ↗</a>
                ) : (
                  <span className={styles.txMuted}>{shortAddress(b.tx_hash, 8, 4)}</span>
                )}
              </span>
            </motion.li>
          );
        })}
      </ol>
    </div>
  );
}

function timeAgo(iso: string): string {
  const t = Date.parse(iso);
  if (isNaN(t)) return iso;
  const d = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (d < 60) return `${d}s ago`;
  if (d < 3600) return `${Math.floor(d / 60)}m ago`;
  if (d < 86400) return `${Math.floor(d / 3600)}h ago`;
  return `${Math.floor(d / 86400)}d ago`;
}
