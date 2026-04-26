/**
 * TS port of packages/watermark/payload.py + _bch.py.
 * Must stay byte-identical to the Python encoder/decoder.
 */

import { TAG_BITS, TAG_END, TAG_START, ZWNJ, ZWSP } from "./constants";

export interface PayloadInfo {
  schemaVersion: number;
  issuerId: number;
  modelId: number;
  modelVersionId: number;
  keyId: number;
  codeValid: boolean;
  errorsCorrected: number;
  rawPayloadHex: string;
}

const POLY = 0x2f;
const INIT = 0xff;
const XOROUT = 0xff;

function crc8(bytes: Uint8Array): number {
  let crc = INIT;
  for (const b of bytes) {
    crc ^= b;
    for (let i = 0; i < 8; i++) {
      crc = crc & 0x80 ? ((crc << 1) ^ POLY) & 0xff : (crc << 1) & 0xff;
    }
  }
  return crc ^ XOROUT;
}

function verifyParity(data56: Uint8Array, parity: number): boolean {
  return crc8(data56) === (parity & 0xff);
}

export function decodePayload(buf: Uint8Array): PayloadInfo {
  if (buf.length !== 8) throw new Error("payload must be 8 bytes");
  const data56 = buf.slice(0, 7);
  const parity = buf[7];

  let corrected: Uint8Array | null = null;
  let errorsCorrected = 0;
  let codeValid = false;

  if (verifyParity(data56, parity)) {
    corrected = data56;
    codeValid = true;
  } else {
    // Single-bit flip search across full 64-bit codeword.
    for (let bit = 0; bit < 64; bit++) {
      const candidate = new Uint8Array(8);
      candidate.set(data56);
      candidate[7] = parity;
      const byteIdx = 7 - Math.floor(bit / 8);
      const bitIdx = bit % 8;
      candidate[byteIdx] ^= 1 << bitIdx;
      const candData = candidate.slice(0, 7);
      const candParity = candidate[7];
      if (verifyParity(candData, candParity)) {
        corrected = candData;
        codeValid = true;
        errorsCorrected = 1;
        break;
      }
    }
    if (corrected === null) {
      corrected = data56;
    }
  }

  // big-endian unpack
  const n =
    (BigInt(corrected[0]) << 48n) |
    (BigInt(corrected[1]) << 40n) |
    (BigInt(corrected[2]) << 32n) |
    (BigInt(corrected[3]) << 24n) |
    (BigInt(corrected[4]) << 16n) |
    (BigInt(corrected[5]) << 8n) |
    BigInt(corrected[6]);

  return {
    schemaVersion: Number((n >> 52n) & 0xfn),
    issuerId: Number((n >> 40n) & 0xfffn),
    modelId: Number((n >> 24n) & 0xffffn),
    modelVersionId: Number((n >> 8n) & 0xffffn),
    keyId: Number(n & 0xffn),
    codeValid,
    errorsCorrected,
    rawPayloadHex: Array.from(buf).map((b) => b.toString(16).padStart(2, "0")).join(""),
  };
}

export function bitsToBytes(bits: string): Uint8Array {
  if (bits.length !== TAG_BITS) throw new Error("expected 64 bits");
  const out = new Uint8Array(8);
  for (let i = 0; i < TAG_BITS; i++) {
    if (bits[i] === "1") out[Math.floor(i / 8)] |= 1 << (7 - (i % 8));
  }
  return out;
}

export function decodeTag(tag: string): string | null {
  if (!tag.startsWith(TAG_START) || !tag.endsWith(TAG_END)) return null;
  const body = tag.slice(TAG_START.length, tag.length - TAG_END.length);
  if (body.length !== TAG_BITS) return null;
  let out = "";
  for (const c of body) {
    if (c === ZWSP) out += "0";
    else if (c === ZWNJ) out += "1";
    else return null;
  }
  return out;
}
