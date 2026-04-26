import { Link } from "react-router-dom";

export function Landing() {
  return (
    <div>
      <h1>Veritext</h1>
      <p style={{ fontSize: 18, color: "var(--color-muted)" }}>
        Cryptographic provenance tags for AI-generated text.
      </p>
      <div className="card">
        <p>
          Veritext binds three things to every piece of AI-generated text:
        </p>
        <ul>
          <li><strong>Identity</strong> — ECDSA secp256k1 signatures via EIP-712 typed data</li>
          <li><strong>Integrity</strong> — invisible Unicode tags with BCH error correction</li>
          <li><strong>Time</strong> — Merkle-batched anchoring to Solana devnet</li>
        </ul>
        <p>
          <Link to="/generate"><button>Try it →</button></Link>
        </p>
      </div>
    </div>
  );
}
