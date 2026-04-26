import { SCAN_TIMEOUT_MS, TAG_END, TAG_START } from "../shared/constants";
import { bitsToBytes, decodePayload, decodeTag, PayloadInfo } from "../shared/payload";

export interface ScanResult {
  textNode: Text;
  startIndex: number;
  endIndex: number;
  raw: string;
  payload: PayloadInfo | null;
}

export class WatermarkScanner {
  scan(root: Node = document.body): ScanResult[] {
    const start = performance.now();
    const results: ScanResult[] = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    while (node) {
      if (performance.now() - start > SCAN_TIMEOUT_MS) break;
      const text = (node as Text).textContent || "";
      let i = 0;
      while (i < text.length) {
        const s = text.indexOf(TAG_START, i);
        if (s === -1) break;
        const e = text.indexOf(TAG_END, s + 1);
        if (e === -1) break;
        const raw = text.slice(s, e + TAG_END.length);
        const bits = decodeTag(raw);
        let payload: PayloadInfo | null = null;
        if (bits !== null) {
          try {
            payload = decodePayload(bitsToBytes(bits));
          } catch {
            payload = null;
          }
        }
        results.push({ textNode: node as Text, startIndex: s, endIndex: e + TAG_END.length, raw, payload });
        i = e + TAG_END.length;
      }
      node = walker.nextNode();
    }
    return results;
  }
}
