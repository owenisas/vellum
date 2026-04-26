export function DemoOverview() {
  return (
    <div>
      <h2>About</h2>
      <div className="card">
        <p>
          Veritext is a <strong>cryptographic provenance tag</strong> system for AI-generated text. It is{" "}
          <em>not</em> a watermark in the SynthID/Kirchenbauer sense — it inserts invisible Unicode tags
          after generation, and signs the bundle.
        </p>
        <p>
          See <a href="/docs/THREAT_MODEL.md">THREAT_MODEL.md</a> for the full threat model. The system targets
          cooperative pipelines (in-scope: copy-paste, accidental edits) and is explicit about what it does not
          defend against (paraphrase, NFKC normalization, deliberate Unicode strip).
        </p>
      </div>
      <div className="card">
        <h3>Compliance</h3>
        <p>
          Veritext is built for <strong>EU AI Act Article 50</strong> (binding August 2026), and aligns with{" "}
          <a href="https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html">
            C2PA 2.2 Content Credentials
          </a>.
        </p>
      </div>
    </div>
  );
}
