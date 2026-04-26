import { Link } from "react-router-dom";
import styles from "./Footer.module.css";

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className={styles.foot}>
      <div className={styles.inner}>
        <div className={styles.col}>
          <span className={styles.brand}>VELLUM</span>
          <p className={styles.tag}>
            Cryptographic provenance for every sentence a machine writes.
          </p>
        </div>
        <div className={styles.col}>
          <span className={styles.colHead}>Product</span>
          <Link to="/studio" className="link-u">Studio</Link>
          <Link to="/ledger" className="link-u">Public ledger</Link>
        </div>
        <div className={styles.col}>
          <span className={styles.colHead}>Read</span>
          <Link to="/principles" className="link-u">Principles</Link>
          <a className="link-u" href="https://artificialintelligenceact.eu/article/50/" target="_blank" rel="noreferrer noopener">EU AI Act, Article 50</a>
          <a className="link-u" href="https://c2pa.org/" target="_blank" rel="noreferrer noopener">C2PA 2.2</a>
        </div>
        <div className={styles.col}>
          <span className={styles.colHead}>Build</span>
          <span className={styles.muted}>{year} · Built on Solana</span>
          <span className={styles.muted}>v2.0 · Devnet</span>
        </div>
      </div>
      <div className={styles.rule} aria-hidden />
    </footer>
  );
}
