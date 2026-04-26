/**
 * Vellum content script entry point.
 *
 * Owns a single {@link WatermarkScanner} + {@link Highlighter} pair, scans the
 * DOM after `DOMContentLoaded`, observes mutations (debounced 300ms), and
 * publishes scan results to the background service worker so the popup can
 * surface them. Also responds to `vellum:rescan` messages from the popup.
 */

import type { WatermarkMeta } from "../shared/payload.js";
import type {
  CandidateText,
  MarkVerifiedMessage,
  RuntimeMessage,
  ScanPayloadSummary,
  ScanResultMessage,
} from "../shared/messages.js";
import { previewText } from "../shared/messages.js";
import { Highlighter, type HighlightMatch } from "./highlighter.js";
import { WatermarkScanner } from "./scanner.js";

const DEBOUNCE_MS = 300;
const MAX_TEXT_NODES = 5000;
const MAX_CANDIDATES = 10;

const scanner = new WatermarkScanner();
const highlighter = new Highlighter();

let observer: MutationObserver | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let lastResult: ScanResultMessage | null = null;
let lastSelectionText = "";
let scanInFlight = false;

const cleanSelectionText = (text: string): string =>
  text
    .replace(/\s*Vellum (?:watermark|verified|not verified)\s*/g, "")
    .trim();

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

const getSelectionText = (): string => {
  const selected = window.getSelection()?.toString() ?? "";
  const trimmed = cleanSelectionText(selected);
  if (trimmed) lastSelectionText = trimmed;
  return trimmed || lastSelectionText;
};

const updateSelectionCache = (): void => {
  const selected = cleanSelectionText(window.getSelection()?.toString() ?? "");
  if (selected) lastSelectionText = selected;
};

const closestTextContainer = (node: Text): Element | null => {
  const start = node.parentElement;
  return (
    start?.closest(
      "article, [role='article'], [data-testid='tweetText'], p, li, blockquote, div",
    ) ?? start
  );
};

const makeCandidate = (
  textNode: Text,
  payload: ScanPayloadSummary,
  seen: Set<string>,
): CandidateText | null => {
  const container = closestTextContainer(textNode);
  const text = (container?.textContent ?? textNode.data).trim();
  if (!text || seen.has(text)) return null;
  seen.add(text);
  return {
    id: `${payload.rawPayloadHex}:${seen.size}`,
    text,
    preview: previewText(text),
    payload,
  };
};

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
        candidates: [],
        selectionText: getSelectionText(),
        url: location.href,
      }
    );
  }
  scanInFlight = true;
  // Pause the observer so highlight DOM mutations don't trigger another scan.
  observer?.disconnect();
  try {
    const selectionText = getSelectionText();
    highlighter.clear();

    const root = document.body;
    const valid: HighlightMatch[] = [];
    const summaries: ScanPayloadSummary[] = [];
    const candidates: CandidateText[] = [];
    const candidateTexts = new Set<string>();
    let invalidCount = 0;

    if (root) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let visited = 0;
      let current = walker.nextNode();
      while (current !== null && visited < MAX_TEXT_NODES) {
        visited++;
        const textNode = current as Text;
        const data = textNode.data;
        if (data && data.length > 0) {
          const matches = scanner.scanText(data);
          for (const m of matches) {
            if (m.crcValid) {
              const payload = summarize(m.payload);
              valid.push({
                node: textNode,
                startIndex: m.startIndex,
                endIndex: m.endIndex,
                meta: m.payload,
              });
              summaries.push(payload);
              if (candidates.length < MAX_CANDIDATES) {
                const candidate = makeCandidate(textNode, payload, candidateTexts);
                if (candidate) candidates.push(candidate);
              }
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
      candidates,
      selectionText,
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
  message: RuntimeMessage,
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
  if (
    typeof message === "object" &&
    message !== null &&
    message.type === "vellum:mark-verified"
  ) {
    const m = message as MarkVerifiedMessage;
    highlighter.markVerification(m.payloadHex, m.verified, m.label);
    sendResponse({ ok: true });
    return true;
  }
  return false;
};

const start = (): void => {
  scanPage();
  attachObserver();
  document.addEventListener("selectionchange", updateSelectionCache);
  document.addEventListener("keyup", updateSelectionCache);
  document.addEventListener("mouseup", updateSelectionCache);
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
