import {
  DEFAULT_API_BASE_URL,
  normalizeApiBaseUrl,
  verifyText,
} from "../shared/api.js";
import type {
  GetSettingsMessage,
  GetStateMessage,
  RuntimeMessage,
  ScanResultMessage,
  ScanState,
  SettingsMessage,
  VerificationState,
  VerifyTextMessage,
} from "../shared/messages.js";

const stateByTab = new Map<number, ScanState>();
const API_BASE_URL_KEY = "apiBaseUrl";

const getApiBaseUrl = async (): Promise<string> => {
  const stored = await chrome.storage.sync.get(API_BASE_URL_KEY);
  return normalizeApiBaseUrl(
    typeof stored[API_BASE_URL_KEY] === "string"
      ? stored[API_BASE_URL_KEY]
      : DEFAULT_API_BASE_URL,
  );
};

const setApiBaseUrl = async (apiBaseUrl: string): Promise<string> => {
  const normalized = normalizeApiBaseUrl(apiBaseUrl);
  await chrome.storage.sync.set({ [API_BASE_URL_KEY]: normalized });
  return normalized;
};

const updateBadge = (
  tabId: number,
  count: number,
  verification?: VerificationState | null,
): void => {
  let text = count > 0 ? String(count) : "";
  let color = "#16a34a";

  if (verification?.result.response?.verified) {
    text = "OK";
    color = "#2563eb";
  } else if (verification && !verification.result.response?.verified) {
    text = "!";
    color = "#dc2626";
  }

  try {
    chrome.action.setBadgeText({
      text,
      tabId,
    });
    chrome.action.setBadgeBackgroundColor({
      color,
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

const isVerifyText = (m: unknown): m is VerifyTextMessage =>
  typeof m === "object" &&
  m !== null &&
  (m as { type?: unknown }).type === "vellum:verify-text";

const isSetApiBaseUrl = (m: unknown): m is SettingsMessage =>
  typeof m === "object" &&
  m !== null &&
  (m as { type?: unknown }).type === "vellum:set-api-base-url";

const isGetSettings = (m: unknown): m is GetSettingsMessage =>
  typeof m === "object" &&
  m !== null &&
  (m as { type?: unknown }).type === "vellum:get-settings";

const markTab = (tabId: number, verification: VerificationState): void => {
  const verified = verification.result.response?.verified === true;
  const reason =
    verification.result.error ??
    verification.result.response?.reason ??
    (verified ? "Verified by Vellum" : "Not verified by Vellum");
  try {
    chrome.tabs.sendMessage(tabId, {
      type: "vellum:mark-verified",
      payloadHex: verification.payloadHex,
      verified,
      label: reason,
    } satisfies RuntimeMessage).catch?.(() => {
      /* content script may be unavailable on browser pages */
    });
  } catch {
    /* ignore */
  }
};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (isScanResult(message)) {
    const tabId = sender.tab?.id;
    if (typeof tabId === "number") {
      const previous = stateByTab.get(tabId);
      stateByTab.set(tabId, {
        count: message.count,
        invalidCount: message.invalidCount,
        payloads: message.payloads,
        candidates: message.candidates,
        selectionText: message.selectionText,
        url: message.url,
        updatedAt: Date.now(),
        verification: previous?.verification ?? null,
      });
      updateBadge(tabId, message.count, previous?.verification ?? null);
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

  if (isGetSettings(message)) {
    getApiBaseUrl().then((apiBaseUrl) => sendResponse({ apiBaseUrl }));
    return true;
  }

  if (isSetApiBaseUrl(message)) {
    setApiBaseUrl(message.apiBaseUrl).then((apiBaseUrl) =>
      sendResponse({ apiBaseUrl }),
    );
    return true;
  }

  if (isVerifyText(message)) {
    const tabId = message.tabId;
    getApiBaseUrl()
      .then((apiBaseUrl) => verifyText(message.text, apiBaseUrl))
      .then((result) => {
        const verification: VerificationState = {
          source: message.source,
          textPreview: message.textPreview,
          payloadHex: message.payloadHex,
          result,
        };
        const current = stateByTab.get(tabId);
        if (current) {
          stateByTab.set(tabId, { ...current, verification });
          updateBadge(tabId, current.count, verification);
        } else {
          updateBadge(tabId, 0, verification);
        }
        markTab(tabId, verification);
        sendResponse({ verification });
      });
    return true;
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
