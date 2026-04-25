import { Link } from "react-router";
import { PageContainer } from "../layout/PageContainer";
import { Card } from "../components/ui";

export function Landing() {
  return (
    <PageContainer>
      <section className="hero">
        <h1>Provenance for AI-generated text</h1>
        <p>
          Vellum proves who generated a piece of text, that it hasn't been
          tampered with, and when it was registered. Watermark-aware, signed,
          and anchored on-chain.
        </p>
        <div className="flex gap-sm" style={{ justifyContent: "center" }}>
          <Link to="/generate" className="btn">
            Try the pipeline
          </Link>
          <Link to="/verify" className="btn btn-secondary">
            Verify text
          </Link>
        </div>
      </section>

      <div className="row">
        <div className="col">
          <Card title="Identity">
            <p className="muted">
              Auth0 JWT identifies the operator. ECDSA on the secp256k1 curve
              proves the issuing company signed the exact bytes you registered.
            </p>
          </Card>
        </div>
        <div className="col">
          <Card title="Integrity">
            <p className="muted">
              Invisible Unicode watermarks embed a 64-bit payload (issuer, model,
              version) into generated text without changing its visible content.
            </p>
          </Card>
        </div>
        <div className="col">
          <Card title="Anchoring">
            <p className="muted">
              Each anchor lives in a SHA-256 linked chain locally and on Solana
              devnet via the Memo program — both auditable independently.
            </p>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}
