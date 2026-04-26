import { describe, expect, it } from "vitest";

import { bitsToBytes, decodePayload, decodeTag } from "../shared/payload";
import { TAG_END, TAG_START, ZWNJ, ZWSP } from "../shared/constants";

describe("payload TS port", () => {
  it("decodes a known-good Python-encoded payload", () => {
    // Generated from `packages/watermark/payload.py` for
    //   Payload(schema_version=1, issuer_id=42, model_id=1001, model_version_id=2, key_id=7)
    // The parity byte is the real BCH parity, so decode must succeed with
    // codeValid=true.
    const knownGoodHex = "102a03e9000207d3";
    const buf = new Uint8Array(
      knownGoodHex.match(/../g)!.map((h) => parseInt(h, 16)),
    );
    const p = decodePayload(buf);
    expect(p.codeValid).toBe(true);
    expect(p.errorsCorrected).toBe(0);
    expect(p.schemaVersion).toBe(1);
    expect(p.issuerId).toBe(42);
    expect(p.modelId).toBe(1001);
    expect(p.modelVersionId).toBe(2);
    expect(p.keyId).toBe(7);
  });

  it("recovers from one-bit corruption (TS port of BCH-Hamming)", () => {
    const buf = new Uint8Array(
      "102a03e9000207d3".match(/../g)!.map((h) => parseInt(h, 16)),
    );
    buf[3] ^= 0b00100000; // flip one bit
    const p = decodePayload(buf);
    expect(p.codeValid).toBe(true);
    expect(p.errorsCorrected).toBe(1);
    expect(p.issuerId).toBe(42);
    expect(p.modelId).toBe(1001);
  });

  it("decodes a tag string", () => {
    const bits = "0".repeat(63) + "1";
    const tag = TAG_START + bits.replace(/0/g, ZWSP).replace(/1/g, ZWNJ) + TAG_END;
    expect(decodeTag(tag)).toBe(bits);
  });

  it("rejects malformed tags", () => {
    expect(decodeTag("not a tag")).toBeNull();
    expect(decodeTag(TAG_START + "abc" + TAG_END)).toBeNull();
  });
});
