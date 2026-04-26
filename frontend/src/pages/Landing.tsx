import { Link } from "react-router-dom";

export function Landing() {
  return (
    <div>
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ marginBottom: "0.25rem", fontSize: "2.5rem" }}>Veritext</h1>
        <p style={{ fontSize: 18, color: "var(--color-muted)", marginTop: 0 }}>
          Cryptographic provenance tags for AI-generated text — invisible at the surface,
          verifiable at the byte.
        </p>
      </header>

      <div className="card" style={{ background: "rgba(79, 70, 229, 0.07)", borderColor: "rgba(79, 70, 229, 0.4)" }}>
        <h2 style={{ marginTop: 0 }}>Try the live demo</h2>
        <p style={{ color: "var(--color-muted)" }}>
          Generate AI text, watch a watermark embed itself, sign it with EIP-712, anchor it on chain,
          and try to tamper with it — all in 4 clicks. No wallet to install. No keys to copy.
        </p>
        <Link to="/demo">
          <button style={{ fontSize: 16, padding: "0.6rem 1.2rem" }}>▶ Start the live demo</button>
        </Link>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>What gets bound to the text</h3>
        <ul>
          <li>
            <strong>Identity</strong> — ECDSA secp256k1 signatures via EIP-712 typed data.
            The browser holds the key; the server only sees signatures.
          </li>
          <li>
            <strong>Integrity</strong> — invisible Unicode tags (BCH(63,16) error-corrected,
            survives copy/paste, base64, NFKC normalization).
          </li>
          <li>
            <strong>Time</strong> — anchored on a simulated chain locally; switch
            <code> CHAIN_BACKEND=solana</code> in <code>.env</code> for Solana devnet with optional
            Merkle batching.
          </li>
        </ul>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Or explore the parts</h3>
        <ul>
          <li><Link to="/generate">Generate &amp; Anchor</Link> — manual flow with full control over fields</li>
          <li><Link to="/verify">Verify</Link> — paste any text, see if it carries a Veritext tag</li>
          <li><Link to="/companies">Companies</Link> — the issuer registry + key rotation</li>
          <li><Link to="/chain">Chain</Link> — block list, tx hashes, simulated/Solana state</li>
          <li><Link to="/dashboard">Dashboard</Link> — system status</li>
        </ul>
      </div>
    </div>
  );
}
