# Veritext Threat Model

> Status: v2.0 — folded in as part of improvement #4 from the implementation plan.

## What Veritext is

Veritext is a **cryptographic provenance tag** for AI-generated text in **cooperative pipelines**. It binds:
- An issuer identity (ECDSA secp256k1 + Auth0 JWT)
- A SHA-256 hash of the text
- A chain timestamp (simulated hash chain or Solana devnet, optionally Merkle-batched)

It is **not** a watermark in the SynthID / Kirchenbauer / Aaronson sense — those modify the LLM's sampling distribution. Veritext inserts invisible Unicode tags **after** generation, and signs the bundle.

The optional `genwatermark` package adds a SynthID-Text generation-time layer as defense in depth, but the primary defense is the post-hoc tag plus the signed bundle.

## In-scope adversaries

These the system is designed to defend against:

| Attack | Mitigation |
|---|---|
| Accidental edit (typos, line wrapping) | BCH(63,16) on each tag corrects 1–2 bit errors |
| Copy-paste through normal browsers / IDEs | Zero-width Unicode preserved; tag survives |
| Substitution of metadata (issuer, timestamp) by republisher | Bundle is JCS-signed — full bundle integrity, not just `sha256(text)` |
| Replay of an old signature on new text | EIP-712 typed-data binds signature to bundle's `text_hash` + `timestamp` |
| Use of a revoked company key | `company_keys` history table; verifier checks key was active at the chain timestamp |

## Out-of-scope adversaries (documented, not defended)

A determined adversary can defeat Veritext's Unicode tag with **one regex**: `re.sub(r"[​-‍⁣⁤]", "", text)`. We **do not pretend otherwise**.

| Attack | Effect |
|---|---|
| Deliberate Unicode strip | Tag deleted; only the SynthID statistical layer (if enabled) survives |
| CMS pipeline that filters invisible chars | Slack, WhatsApp, some CMSes regex-strip these characters. This is *not* NFKC alone — pure `unicodedata.normalize("NFKC", ...)` preserves U+200B/U+200C/U+2063/U+2064. The attack is the additional filter on top of NFKC. |
| Paraphrase / rewrite via another LLM | Words change; Unicode tag is gone; SynthID statistical signal degrades or vanishes |
| Translation | Same as paraphrase |
| OCR / re-typing | All invisible chars lost |

For these adversaries, **content provenance must rely on**:
1. The C2PA-style manifest (the signed bundle stored externally — link from publisher metadata)
2. The optional SynthID generation-time layer (statistical, partial robustness)
3. Out-of-band attestation (publisher's key + signed claim)

## Recommended deployment posture

- Treat Veritext as a **provenance signal in cooperative pipelines** (your apps, your customers' uploads, your own browser extension).
- Use **Merkle-batched anchoring** (`ANCHOR_STRATEGY=merkle_batch`) at scale — single Solana transactions per response do not scale.
- Enable **`PAYLOAD_VISIBILITY=encrypted`** if you do not want issuer/model metadata leaked publicly.
- Enable **`GENWATERMARK_ENABLED=true`** for defense in depth, but do not market it as paraphrase-robust.
- Pair Veritext with **publisher-side metadata** (C2PA-aligned bundle JSON delivered alongside content).

## Cryptographic assumptions

- secp256k1 ECDSA is hard (standard).
- SHA-256 is collision-resistant (standard).
- BCH(63,16) corrects up to 7-bit errors (correct; theoretical floor `floor((d-1)/2)` where `d ≥ 15`).
- AES-128-CCM with unique 96-bit nonces per encrypted payload (NIST SP 800-38C).
- RFC 8785 JCS produces a single canonical UTF-8 byte sequence per JSON value.
- EIP-712 domain separator `{name: "Veritext", version: "2", chainId, verifyingContract}` is **immutable once published**.

## Disclosure & reporting

Security issues: report via GitHub Security Advisories. We follow a 90-day coordinated disclosure window.
