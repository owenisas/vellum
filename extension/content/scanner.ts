/**
 * DOM + text scanning for embedded zero-width watermark tags.
 *
 * The regex is constructed at runtime from the imported constants so the
 * Unicode codepoints never appear literally in source — this keeps the file
 * grep-friendly and makes the format trivial to retarget.
 */

import { TAG_BITS, TAG_END, TAG_START, ZWNJ, ZWSP } from "../shared/constants.js";
import { unpackPayload, type WatermarkMeta } from "../shared/payload.js";

export interface ScanResult {
  /** Index of the first character of TAG_START in the source string. */
  startIndex: number;
  /** Index immediately after TAG_END in the source string. */
  endIndex: number;
  payload: WatermarkMeta;
  crcValid: boolean;
  rawBits: string;
}

/** Maximum number of text nodes we'll process for a single `scan()` call. */
const MAX_NODES = 5000;

/** Escape a single Unicode codepoint for safe insertion into a regex. */
const escapeForRegex = (ch: string): string =>
  ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const buildTagPattern = (): RegExp => {
  const start = escapeForRegex(TAG_START);
  const end = escapeForRegex(TAG_END);
  const zero = escapeForRegex(ZWSP);
  const one = escapeForRegex(ZWNJ);
  // Non-greedy match on the bit chars so adjacent tags don't merge.
  return new RegExp(`${start}([${zero}${one}]+?)${end}`, "gu");
};

const decodeBits = (bitChars: string): string => {
  let out = "";
  for (const c of bitChars) {
    if (c === ZWSP) out += "0";
    else if (c === ZWNJ) out += "1";
  }
  return out;
};

export class WatermarkScanner {
  /** Pre-compiled tag pattern; flags are sticky-free, so `lastIndex` resets per use. */
  private readonly pattern = buildTagPattern();

  /** Find every well-formed watermark tag in a single string. */
  scanText(text: string): ScanResult[] {
    if (!text) return [];

    // Fresh RegExp avoids cross-call lastIndex leaks if a consumer aborts mid-iteration.
    const pattern = new RegExp(this.pattern.source, this.pattern.flags);
    const results: ScanResult[] = [];

    let match: RegExpExecArray | null;
    while ((match = pattern.exec(text)) !== null) {
      const bits = decodeBits(match[1]);
      if (bits.length !== TAG_BITS) continue;

      let payload: WatermarkMeta;
      try {
        payload = unpackPayload(bits);
      } catch {
        continue;
      }

      results.push({
        startIndex: match.index,
        endIndex: match.index + match[0].length,
        payload,
        crcValid: payload.crcValid,
        rawBits: bits,
      });
    }

    return results;
  }

  /**
   * Walk the DOM beneath `root` and return every watermark found in text nodes.
   *
   * Bounded at {@link MAX_NODES} text nodes to keep pathological pages snappy.
   */
  scan(root: Node = document.body): Array<ScanResult & { node: Text }> {
    if (!root) return [];

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const out: Array<ScanResult & { node: Text }> = [];

    let visited = 0;
    let current = walker.nextNode();
    while (current !== null && visited < MAX_NODES) {
      visited++;
      const textNode = current as Text;
      const data = textNode.data;
      if (data && data.length > 0) {
        const matches = this.scanText(data);
        for (const m of matches) {
          out.push({ ...m, node: textNode });
        }
      }
      current = walker.nextNode();
    }

    return out;
  }
}
