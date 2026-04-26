/**
 * Vellum content script entry point.
 *
 * Owns a single {@link WatermarkScanner} + {@link Highlighter} pair, scans the
 * DOM after `DOMContentLoaded`, observes mutations (debounced 300ms), and
 * publishes scan results to the background service worker so the popup can
 * surface them. Also responds to `vellum:rescan` messages from the popup.
 */

import type { WatermarkMeta } from "../shared/payload.js";
import { Highlighter, type HighlightMatch } from "./highlighter.js";
import { WatermarkScanner } from "./scanner.js";

interface ScanPayloadSummary {
  schemaVersion: number;
  issuerId: number;
  modelId: number;
  modelVersionId: number;
  keyId: number;
  crc: number;
  crcValid: boolean;
  rawPayloadHex: string;
}

interface ScanResultMessage {
  type: "vellum:scan-result";
  count: number;
  invalidCount: number;
  payloads: ScanPayloadSummary[];
  url: string;
}

const DEBOUNCE_MS = 300;

const scanner = new WatermarkScanner();
const highlighter = new Highlighter();

let observer: MutationObserver | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let lastResult: ScanResultMessage | null = null;
let scanInFlight = false;

const summarize = (meta: WatermarkMeta): ScanPayloadSummary => ({
  schemaVersion: meta.schemaVersion,
  issuerId: meta.issuerId,
  modelId: meta.modelId,
  modelVersionId: meta.modelVersionId,
  keyId: meta.keyId,
  crc: meta.crc,
  crcValid: meta.crcValid,
  rawPayloadHex: meta.rawPayloadHex,
});

const publishResult = (msg: ScanResultMessage): void => {
  lastResult = msg;
  try {
    if (typeof chrome !== "undefined" && chrome.runtime?.id) {
      chrome.runtime.sendMessage(msg).catch?.(() => {
        /* ignore: SW may be sleeping or no listener */
      });
    }
  } catch {
    /* runtime not available (e.g. detached frame) */
  }
};

const scanPage = (): ScanResultMessage => {
  if (scanInFlight) {
    // Re-entrant calls during DOM mutation; return last known.
    return (
      lastResult ?? {
        type: "vellum:scan-result",
        count: 0,
        invalidCount: 0,
        payloads: [],
        url: location.href,
      }
    );
  }
  scanInFlight = true;
  // Pause the observer so highlight DOM mutations don't trigger another scan.
  observer?.disconnect();
  try {
    highlighter.clear();

    const root = document.body;
    const valid: HighlightMatch[] = [];
    const summaries: ScanPayloadSummary[] = [];
    let invalidCount = 0;

    if (root) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let visited = 0;
      let current = walker.nextNode();
      while (current !== null && visited < 5000) {
        visited++;
        const textNode = current as Text;
        const data = textNode.data;
        if (data && data.length > 0) {
          const matches = scanner.scanText(data);
          for (const m of matches) {
            if (m.crcValid) {
              valid.push({
                node: textNode,
                startIndex: m.startIndex,
                endIndex: m.endIndex,
                meta: m.payload,
              });
              summaries.push(summarize(m.payload));
            } else {
              invalidCount++;
            }
          }
        }
        current = walker.nextNode();
      }
    }

    highlighter.highlight(valid);

    const msg: ScanResultMessage = {
      type: "vellum:scan-result",
      count: valid.length,
      invalidCount,
      payloads: summaries,
      url: location.href,
    };
    publishResult(msg);
    return msg;
  } finally {
    scanInFlight = false;
    attachObserver();
  }
};

const scheduleScan = (): void => {
  if (debounceTimer !== null) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    debounceTimer = null;
    scanPage();
  }, DEBOUNCE_MS);
};

const attachObserver = (): void => {
  if (!document.body) return;
  if (!observer) {
    observer = new MutationObserver((mutations) => {
      // Skip our own highlight mutations: they only ever touch
      // `.vellum-detected` / `.vellum-badge` nodes.
      for (const mut of mutations) {
        const target = mut.target as Element | null;
        if (
          target &&
          target.nodeType === Node.ELEMENT_NODE &&
          (target.classList?.contains("vellum-detected") ||
            target.classList?.contains("vellum-badge"))
        ) {
          continue;
        }
        scheduleScan();
        return;
      }
    });
  }
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
};

const handleMessage = (
  message: unknown,
  _sender: chrome.runtime.MessageSender,
  sendResponse: (response: unknown) => void,
): boolean => {
  if (
    typeof message === "object" &&
    message !== null &&
    (message as { type?: unknown }).type === "vellum:rescan"
  ) {
    const result = scanPage();
    sendResponse(result);
    return true;
  }
  return false;
};

const start = (): void => {
  scanPage();
  attachObserver();
  try {
    chrome.runtime.onMessage.addListener(handleMessage);
  } catch {
    /* runtime not present */
  }
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start, { once: true });
} else {
  start();
}
