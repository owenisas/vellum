import { motion } from "framer-motion";
import { Link } from "react-router-dom";

import { DisplayHeading } from "../components/ui/DisplayHeading";
import { EditorialCaption } from "../components/ui/EditorialCaption";
import { MagneticButton } from "../components/ui/MagneticButton";
import { ease } from "../lib/motion";
import styles from "./Principles.module.css";

export function Principles() {
  return (
    <motion.section
      key="principles"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4, ease }}
      className={styles.shell}
    >
      <header className={`container ${styles.head}`}>
        <EditorialCaption number="N°04" rule>PRINCIPLES</EditorialCaption>
        <DisplayHeading as="h1" italicWords={["why"]} className={styles.title}>
          {"What we believe,\nand why."}
        </DisplayHeading>
        <p className={styles.lede}>
          Vellum is not a watermark for catching cheaters. It is a quiet
          piece of infrastructure that lets a sentence carry its origin
          everywhere it goes.
        </p>
      </header>

      <article className={`container ${styles.article}`}>
        <PullQuote>
          A machine wrote this. Someone vouched for it. Anyone can check.
        </PullQuote>

        <Section
          number="I"
          marker={<DiamondMark />}
          title="The problem"
          subtitle="Words have stopped looking like they came from anywhere."
        >
          <p>
            Most of the text we read each day no longer comes from a person we
            know, or even a person at all. Models write headlines, evidence,
            term sheets, school essays, and product reviews. They do it well
            enough that we can&apos;t tell the difference, and the people
            making decisions on those words can&apos;t either.
          </p>
          <p>
            The fix is not to <em>detect</em> machine writing after the fact.
            Detectors are guesses, and guesses lose to better models every
            year. The fix is to give every sentence a way to carry its origin
            forward — verifiably, durably, without changing how it reads.
          </p>
          <p>
            That is what regulators are now requiring. The European AI Act,
            Article 50<Sup n="1" />, will require every machine-generated text
            to be marked in a way a machine can read. The C2PA standard<Sup n="2" />
            is shaping the same expectation across photo, audio, and video.
            The question is no longer whether provenance is needed — it is
            who builds it well.
          </p>
        </Section>

        <Section
          number="II"
          marker={<TriangleMark />}
          title="The method"
          subtitle="Three layers, each independently verifiable."
        >
          <p>
            <strong>An invisible signature.</strong> When the model writes,
            we braid into the text a sequence of zero-width Unicode
            characters — bytes that take up no space, are invisible to a
            human reader, and survive copy-paste, translation, and most
            edits. Inside is a 64-bit payload, error-corrected, that names
            the issuer, the model, the model version, and the key.
          </p>
          <p>
            <strong>A cryptographic seal.</strong> Before the paragraph
            leaves the studio, the issuer&apos;s private key signs its
            fingerprint. Anyone with the matching public key can confirm the
            signature came from that issuer and no one else. We use the same
            elliptic-curve cryptography that secures Ethereum and Bitcoin —
            an open standard, no proprietary magic.
          </p>
          <p>
            <strong>A verifiable registry.</strong> The signed fingerprint is
            anchored into a tamper-evident registry. For the no-funds demo,
            browser wallets sign messages rather than transactions, so users
            prove wallet control without gas, SOL, or spend permissions. A
            future on-chain mode can verify wallet-submitted Solana Memo
            transactions without giving the backend custody of user funds.
          </p>
          <p>
            Three layers. If one is removed, the others still tell the
            truth. If all three pass, you know who wrote it, when, and that
            it has not been changed.
          </p>
        </Section>

        <Section
          number="III"
          marker={<HexMark />}
          title="The commitment"
          subtitle="Open, durable, never extractive."
        >
          <p>
            Vellum is a public good wearing the clothes of a startup. The
            verifier will always be free, the bundles will always be
            inspectable offline, and the registry will always be open.
            Issuers pay the cost of anchoring; readers pay nothing.
          </p>
          <p>
            We will not retain text we anchor. The fingerprint goes on chain;
            the words stay where they were written. We will not sell access
            to anything. We will not introduce a private API the open
            standard cannot reach. If we build something that fails this
            test, it does not ship.
          </p>
          <p>
            For a longer technical statement, see the threat model and the
            full proof-bundle specification on GitHub. For the regulators
            among you, the AI-Act compliance summary is published with each
            release.
          </p>
        </Section>

        <footer className={styles.foot}>
          <ol className={styles.notes}>
            <li>
              <span className={styles.noteNum}>1</span>
              EU AI Act, Article 50 — disclosure obligations for providers and
              deployers of certain AI systems, binding from 2026-08-02.{" "}
              <a className="link-u" href="https://artificialintelligenceact.eu/article/50/" target="_blank" rel="noreferrer noopener">
                artificialintelligenceact.eu/article/50
              </a>
            </li>
            <li>
              <span className={styles.noteNum}>2</span>
              C2PA — Coalition for Content Provenance and Authenticity, v2.2 specification.{" "}
              <a className="link-u" href="https://c2pa.org/specifications/specifications/2.2/index.html" target="_blank" rel="noreferrer noopener">
                c2pa.org/specifications
              </a>
            </li>
          </ol>

          <div className={styles.cta}>
            <span className={styles.ctaCap}>NEXT</span>
            <MagneticButton to="/studio" variant="filled">Try the studio</MagneticButton>
            <Link to="/" className={`link-u ${styles.ctaBack}`}>Return to the cover</Link>
          </div>
        </footer>
      </article>
    </motion.section>
  );
}

function PullQuote({ children }: { children: React.ReactNode }) {
  return (
    <motion.blockquote
      className={styles.pull}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.9, ease, delay: 0.2 }}
    >&ldquo;{children}&rdquo;</motion.blockquote>
  );
}

function Sup({ n }: { n: string }) {
  return (
    <a className={styles.sup} href={`#note-${n}`}>
      <sup>{n}</sup>
    </a>
  );
}

function Section({
  number, marker, title, subtitle, children,
}: { number: string; marker: React.ReactNode; title: string; subtitle: string; children: React.ReactNode; }) {
  return (
    <motion.section
      className={styles.section}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease }}
    >
      <header className={styles.sectionHead}>
        <span className={styles.sectionNum}>{number}</span>
        <span className={styles.marker}>{marker}</span>
        <div>
          <h2 className={styles.sectionTitle}>{title}</h2>
          <p className={styles.sectionSub}>{subtitle}</p>
        </div>
      </header>
      <div className={styles.prose}>{children}</div>
    </motion.section>
  );
}

function DiamondMark() {
  return (
    <svg viewBox="-12 -12 24 24" width="22" height="22" aria-hidden>
      <polygon points="0,-10 10,0 0,10 -10,0" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <circle r="2" fill="var(--signal)" />
    </svg>
  );
}
function TriangleMark() {
  return (
    <svg viewBox="-12 -12 24 24" width="22" height="22" aria-hidden>
      <polygon points="0,-10 9,7 -9,7" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <line x1="0" y1="-10" x2="0" y2="7" stroke="var(--signal)" strokeWidth="1" />
    </svg>
  );
}
function HexMark() {
  return (
    <svg viewBox="-12 -12 24 24" width="22" height="22" aria-hidden>
      <polygon points="0,-10 9,-5 9,5 0,10 -9,5 -9,-5" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <circle r="3" fill="none" stroke="var(--signal)" strokeWidth="1" />
    </svg>
  );
}
