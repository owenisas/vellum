/**
 * Vellum background service worker.
 *
 * Maintains a per-tab cache of the most recent scan result reported by content
 * scripts, paints the action badge, and answers `vellum:get-state` queries
 * from the popup.
 */

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

interface GetStateMessage {
  type: "vellum:get-state";
  tabId?: number;
}

interface ScanState {
  count: number;
  invalidCount: number;
  payloads: ScanPayloadSummary[];
  url: string;
  updatedAt: number;
}

const stateByTab = new Map<number, ScanState>();

const updateBadge = (tabId: number, count: number): void => {
  try {
    chrome.action.setBadgeText({
      text: count > 0 ? String(count) : "",
      tabId,
    });
    chrome.action.setBadgeBackgroundColor({
      color: "#16a34a",
      tabId,
    });
  } catch {
    /* badge APIs unavailable in this context */
  }
};

const isScanResult = (m: unknown): m is ScanResultMessage =>
  typeof m === "object" &&
  m !== null &&
  (m as { type?: unknown }).type === "vellum:scan-result";

const isGetState = (m: unknown): m is GetStateMessage =>
  typeof m === "object" &&
  m !== null &&
  (m as { type?: unknown }).type === "vellum:get-state";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (isScanResult(message)) {
    const tabId = sender.tab?.id;
    if (typeof tabId === "number") {
      stateByTab.set(tabId, {
        count: message.count,
        invalidCount: message.invalidCount,
        payloads: message.payloads,
        url: message.url,
        updatedAt: Date.now(),
      });
      updateBadge(tabId, message.count);
    }
    sendResponse({ ok: true });
    return false;
  }

  if (isGetState(message)) {
    const tabId =
      typeof message.tabId === "number" ? message.tabId : sender.tab?.id;
    const state =
      typeof tabId === "number" ? stateByTab.get(tabId) ?? null : null;
    sendResponse({ tabId, state });
    return false;
  }

  return false;
});

// Drop cached state when tabs go away so the map can't grow without bound.
chrome.tabs.onRemoved.addListener((tabId) => {
  stateByTab.delete(tabId);
});

// Reset state on full navigation so stale counts don't leak across pages.
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading" && changeInfo.url) {
    stateByTab.delete(tabId);
    updateBadge(tabId, 0);
  }
});
