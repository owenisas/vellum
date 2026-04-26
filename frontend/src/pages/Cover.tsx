import { lazy, Suspense, useEffect, useState } from "react";
import { motion } from "framer-motion";

import { DisplayHeading } from "../components/ui/DisplayHeading";
import { EditorialCaption } from "../components/ui/EditorialCaption";
import { MagneticButton } from "../components/ui/MagneticButton";
import { IcosahedronFallback } from "../components/scenes/IcosahedronFallback";
import { ease, prefersReducedMotion } from "../lib/motion";
import styles from "./Cover.module.css";

const IcosahedronScene = lazy(() => import("../components/scenes/IcosahedronScene"));

const COVER_LINES = [
  {
    no: "01",
    head: "WRITE",
    body: "Generate text that already carries an invisible signature — bound to your identity at the moment it is made.",
  },
  {
    no: "02",
    head: "SIGN",
    body: "Auth0 and browser-wallet signatures bind the words to accountable identities without exposing keys or requiring gas.",
  },
  {
    no: "03",
    head: "PROVE",
    body: "Anyone, anywhere, can paste a paragraph and learn who wrote it, when it was written, and whether a single word has changed.",
  },
];

export function Cover() {
  const [show3D, setShow3D] = useState(false);
  useEffect(() => {
    if (prefersReducedMotion()) return;
    const mq = window.matchMedia("(min-width: 720px)");
    if (!mq.matches) return;
    const t = setTimeout(() => setShow3D(true), 80);
    return () => clearTimeout(t);
  }, []);

  return (
    <motion.section
      key="cover"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4, ease }}
      className={styles.page}
    >
      <div className={styles.stage} aria-hidden>
        <Suspense fallback={<IcosahedronFallback />}>
          {show3D ? <IcosahedronScene /> : <IcosahedronFallback />}
        </Suspense>
        <div className={styles.vignette} />
      </div>

      <div className={`container ${styles.head}`}>
        <EditorialCaption number="N°01" rule>PROVENANCE — MMXXVI</EditorialCaption>
        <span className={styles.headIssue}>JANUARY · MMXXVI</span>
      </div>

      <div className={`container ${styles.hero}`}>
        <div className={styles.heroLeft}>
          <span className={styles.kicker}>A FIELD GUIDE TO</span>
          <DisplayHeading className={styles.title} italicWords={["machine"]}>
            {"Every sentence\na machine writes\ncan be proven."}
          </DisplayHeading>
          <motion.p
            className={styles.lede}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease, delay: 1.1 }}
          >
            Vellum signs and seals AI-written text with Auth0 identity,
            browser-wallet proofs, and a tamper-evident registry, so authorship,
            time, and integrity stay readable without asking anyone to fund a wallet.
          </motion.p>
          <motion.div
            className={styles.actions}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease, delay: 1.3 }}
          >
            <MagneticButton to="/studio" variant="filled">
              Enter the Studio
            </MagneticButton>
            <MagneticButton to="/principles" variant="outline" arrow={false}>
              Read the Principles
            </MagneticButton>
          </motion.div>
        </div>

        <aside className={styles.rail} aria-label="Cover lines">
          {COVER_LINES.map((c, i) => (
            <motion.div
              key={c.no}
              className={styles.line}
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease, delay: 0.7 + i * 0.18 }}
            >
              <span className={styles.lineNo}>{c.no}</span>
              <div>
                <h3 className={styles.lineHead}>{c.head}</h3>
                <p className={styles.lineBody}>{c.body}</p>
              </div>
            </motion.div>
          ))}
        </aside>
      </div>

      <div className={`container ${styles.foot}`}>
        <span className={styles.footMono}>
          NO-FUNDS WALLET PROOFS · OPEN-SOURCE · COMPLIANT WITH EU AI ACT, ARTICLE 50
        </span>
        <span className={styles.scrollHint} aria-hidden>↓ SCROLL</span>
      </div>
    </motion.section>
  );
}
