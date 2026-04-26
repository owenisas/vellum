import { PageContainer } from "../layout/PageContainer";
import { Card } from "../components/ui";

export function DemoOverview() {
  return (
    <PageContainer
      title="How Vellum works"
      subtitle="Three orthogonal layers: identity, integrity, and anchoring."
    >
      <Card title="1. Identity (Auth0 + ECDSA)">
        <p>
          Auth0 issues an OIDC JWT that identifies <em>who</em> is calling the
          API. The JWT carries scopes (<code>chat:invoke</code>,{" "}
          <code>anchor:create</code>, <code>company:create</code>) and an
          optional <code>https://vellum.io/issuer_id</code> claim.
        </p>
        <p>
          On top of that, every anchored record is signed with a per-company
          secp256k1 keypair using EIP-191 personal_sign. The server recovers
          the address from the signature and matches it against the registered
          company.
        </p>
      </Card>

      <Card title="2. Integrity (invisible watermarks)">
        <p>
          Vellum injects a 64-bit payload into generated text using
          zero-width Unicode characters (<code>U+200B</code>,{" "}
          <code>U+200C</code>) wrapped between invisible separators (
          <code>U+2063</code>, <code>U+2064</code>).
        </p>
        <p>
          The payload encodes <code>schema_version</code>, <code>issuer_id</code>,{" "}
          <code>model_id</code>, <code>model_version_id</code>, <code>key_id</code>{" "}
          and a CRC-8 checksum. The text reads identically — but the watermark
          survives copy-paste across Slack, email, and most HTML.
        </p>
      </Card>

      <Card title="3. Anchoring (SQLite + Solana)">
        <p>
          Anchors live in a SHA-256 linked chain backed by{" "}
          <code>aiosqlite</code>. With <code>CHAIN_BACKEND=solana</code>, each
          anchor also writes a Memo program transaction to Solana devnet, and
          the local block stores the resulting tx signature for explorer
          links.
        </p>
        <p>
          Every record produces a Proof Bundle v2 — a self-verifiable JSON
          document containing the issuer, signature, watermark info, anchor
          receipt, and verification hints (RPC URLs, explorer links).
        </p>
      </Card>

      <Card title="Try it">
        <p>
          The <a href="/demo">Guided demo</a> page walks through every step in
          fixture mode. Or hit <a href="/generate">Generate &amp; Anchor</a> for
          the full live pipeline.
        </p>
      </Card>
    </PageContainer>
  );
}
