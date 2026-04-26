# Veritext Compliance Matrix

## EU AI Act — Article 50 (binding August 2026)

| Article 50 obligation | Veritext mechanism | Implementation |
|---|---|---|
| 50(2) Machine-readable marking of synthetic text | Invisible Unicode payload tag (BCH-protected) | `packages/watermark/` |
| 50(2) Reliable, interoperable detection | Stateless `veritext-verify` CLI + Chrome extension | `cli/`, `extension/` |
| 50(4) Visible disclosure for public-interest text | Frontend UI explicitly labels output as AI-generated | `frontend/src/pages/GenerateAndAnchor.tsx` |
| Code of Practice — multi-layered marking | Post-hoc Unicode tag + optional generation-time SynthID | `packages/watermark/` + `packages/genwatermark/` |
| Robustness to "common modifications" | Copy-paste survives; documented limits (paraphrase, NFKC) | `docs/THREAT_MODEL.md`, `tests/adversarial/` |
| Provider transparency | OpenAPI docs + signed bundles published to clients | `src/veritext/api/` |

## C2PA 2.2 alignment

Veritext is a text-asset provenance system. C2PA 2.2 covers manifests for binary assets (images, video, audio, documents). The Veritext proof bundle aligns conceptually with the C2PA Manifest, with the following field correspondences:

| C2PA 2.2 manifest field | Veritext bundle field | Notes |
|---|---|---|
| `claim_generator` | `issuer.name` | Human-readable issuer |
| `claim_generator_info[].name` | `issuer.name` + `issuer.public_key_hex` | Cryptographic identity |
| `signature` (COSE) | `signature` (EIP-712 secp256k1) | Different signing format; same intent |
| `assertions[].label` | `signed_fields[]` | What the signature commits to |
| `created` (timestamp) | `anchors[].timestamp` | Chain-attested |
| `parent` (provenance link) | future field `parent_bundle_id` | TODO v2.1 |
| `c2pa.training_mining` | `watermark.generation_time.*` | When SynthID is active |

**Divergence**: Veritext uses RFC 8785 JCS canonicalization + EIP-712 secp256k1 signing instead of CBOR/COSE — chosen for Ethereum tooling reuse and browser-side wallet UX. A C2PA-compatible export (`/api/proof/{id}?format=c2pa`) is planned for v2.1.

## NIST AI Risk Management Framework

| NIST AI RMF function | Veritext capability |
|---|---|
| GOVERN | `docs/THREAT_MODEL.md`, key rotation, audit trail in `chain_blocks` |
| MAP | Issuer registry; per-model `model_id` / `model_version_id` in payload |
| MEASURE | Adversarial test suite `tests/adversarial/` produces detection-rate report per CI run |
| MANAGE | Company key rotation endpoint with grace period; revocation via `company_keys.active=false` |

## References

- [EU AI Act Article 50 (consolidated)](https://artificialintelligenceact.eu/article/50/)
- [EU AI Code of Practice — content marking](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)
- [C2PA 2.2 Technical Specification](https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html)
- [NIST AI 100-1 — AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)
