/**
 * 64-bit watermark payload helpers.
 *
 * This module is a faithful TypeScript port of `packages/watermark/payload.py`.
 * The CRC-8 implementation, bit layout, and field shifts must match exactly so
 * that payloads produced by the Python encoder round-trip through this decoder.
 *
 * Layout (MSB first):
 *   [63:60] schema_version    4 bits
 *   [59:48] issuer_id        12 bits
 *   [47:32] model_id         16 bits
 *   [31:16] model_version_id 16 bits
 *   [15:8]  key_id            8 bits
 *   [7:0]   crc8              8 bits  (poly 0x07, MSB feedback, init 0)
 */

import { TAG_BITS } from "./constants.js";

/**
 * Standard CRC-8 with polynomial 0x07, MSB feedback, initial value 0.
 *
 * Mirrors `packages/watermark/payload.py::crc8` byte-for-byte.
 */
export const crc8 = (data: Uint8Array): number => {
  let crc = 0;
  for (let i = 0; i < data.length; i++) {
    crc ^= data[i] & 0xff;
    for (let bit = 0; bit < 8; bit++) {
      if ((crc & 0x80) !== 0) {
        crc = ((crc << 1) ^ 0x07) & 0xff;
      } else {
        crc = (crc << 1) & 0xff;
      }
    }
  }
  return crc;
};

export interface WatermarkMeta {
  schemaVersion: number;
  issuerId: number;
  modelId: number;
  modelVersionId: number;
  keyId: number;
  crc: number;
  crcValid: boolean;
  rawPayloadHex: string;
}

/** Convert a 64-character binary string to a 0x-prefixed 16-char hex string. */
export const bitsToHex = (bits: string): string => {
  if (bits.length !== TAG_BITS) {
    throw new Error(`bitsToHex: expected ${TAG_BITS} bits, got ${bits.length}`);
  }
  if (!/^[01]+$/.test(bits)) {
    throw new Error("bitsToHex: bits must contain only '0' and '1'");
  }
  const value = BigInt("0b" + bits);
  return "0x" + value.toString(16).padStart(16, "0");
};

/**
 * Decode a 64-bit binary string into a {@link WatermarkMeta} record.
 *
 * Performs CRC-8 validation over the high 56 bits and reports the result via
 * `crcValid` rather than throwing — invalid payloads are still returned so
 * callers can surface counts of corrupted tags.
 */
export const unpackPayload = (bits: string): WatermarkMeta => {
  if (bits.length !== TAG_BITS) {
    throw new Error(
      `unpackPayload: expected ${TAG_BITS} bits, got ${bits.length}`,
    );
  }
  if (!/^[01]+$/.test(bits)) {
    throw new Error("unpackPayload: bits must contain only '0' and '1'");
  }

  const payload = BigInt("0b" + bits);

  const schemaVersion = Number((payload >> 60n) & 0xfn);
  const issuerId = Number((payload >> 48n) & 0xfffn);
  const modelId = Number((payload >> 32n) & 0xffffn);
  const modelVersionId = Number((payload >> 16n) & 0xffffn);
  const keyId = Number((payload >> 8n) & 0xffn);
  const crc = Number(payload & 0xffn);

  // Recompute CRC over the high 56 bits, packed big-endian into 7 bytes.
  const high56 = payload >> 8n;
  const high56Bytes = new Uint8Array(7);
  for (let i = 0; i < 7; i++) {
    // Most-significant byte first.
    const shift = BigInt((6 - i) * 8);
    high56Bytes[i] = Number((high56 >> shift) & 0xffn);
  }
  const expectedCrc = crc8(high56Bytes);

  return {
    schemaVersion,
    issuerId,
    modelId,
    modelVersionId,
    keyId,
    crc,
    crcValid: crc === expectedCrc,
    rawPayloadHex: "0x" + payload.toString(16).padStart(16, "0"),
  };
};
