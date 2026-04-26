import { Link } from "react-router-dom";

export function GuidedDemo() {
  return (
    <div>
      <h2>Guided Demo</h2>
      <ol>
        <li><Link to="/companies">Register a company</Link> with a private key.</li>
        <li><Link to="/generate">Generate watermarked text</Link> using the fixture provider.</li>
        <li>Sign with the same private key (EIP-712).</li>
        <li>Anchor — view the proof bundle.</li>
        <li><Link to="/verify">Verify</Link> the text by pasting it back.</li>
        <li>Optionally <Link to="/chain">browse the chain</Link>.</li>
      </ol>
    </div>
  );
}
