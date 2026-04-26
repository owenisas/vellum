import { motion } from "framer-motion";
import { useCompanies } from "../../api/companies";
import { ease } from "../../lib/motion";
import { shortAddress } from "../../lib/hash";
import styles from "./IssuerList.module.css";

export function IssuerList({ onAdmin }: { onAdmin?: () => void }) {
  const { data, isLoading } = useCompanies();
  const list = data ?? [];
  return (
    <section className={styles.wrap}>
      <header className={styles.head}>
        <span className={styles.cap}>ISSUERS</span>
        {onAdmin && (
          <button type="button" className={styles.adminBtn} onClick={onAdmin}>Admin</button>
        )}
      </header>
      {isLoading && <p className={styles.empty}>Loading…</p>}
      {!isLoading && list.length === 0 && (
        <p className={styles.empty}>No issuers registered yet.</p>
      )}
      <ul className={styles.list}>
        {list.map((c, i) => (
          <motion.li
            key={c.issuer_id}
            className={styles.row}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease, delay: i * 0.04 }}
          >
            <div className={styles.who}>
              <span className={styles.name}>{c.name}</span>
              <span className={styles.id}>#{c.issuer_id}</span>
            </div>
            <span className={styles.addr}>{shortAddress(c.eth_address, 8, 6)}</span>
            <span className={styles.key}>
              key v{c.current_key_id}
              {c.key_history.length > 1 && <sup className={styles.sup}>·{c.key_history.length}</sup>}
            </span>
          </motion.li>
        ))}
      </ul>
    </section>
  );
}
