// shared/api.ts
var DEFAULT_API_BASE_URL = "https://vellum-387oq.ondigitalocean.app";
var normalizeApiBaseUrl = (value) => {
  const raw = (value ?? DEFAULT_API_BASE_URL).trim().replace(/\/+$/, "");
  if (!raw) return DEFAULT_API_BASE_URL;
  if (!/^https?:\/\//i.test(raw)) return `https://${raw}`;
  return raw;
};
var verifyText = async (text, apiBaseUrl) => {
  const base = normalizeApiBaseUrl(apiBaseUrl);
  const checkedAt = Date.now();
  try {
    const resp = await fetch(`${base}/api/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    if (!resp.ok) {
      let detail = `${resp.status} ${resp.statusText}`.trim();
      try {
        const body = await resp.json();
        if (typeof body.detail === "string") detail = body.detail;
      } catch {
      }
      return {
        ok: false,
        apiBaseUrl: base,
        checkedAt,
        error: `Verifier request failed: ${detail}`
      };
    }
    const response = await resp.json();
    return { ok: true, apiBaseUrl: base, checkedAt, response };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      apiBaseUrl: base,
      checkedAt,
      error: `Could not reach verifier: ${message}`
    };
  }
};

// background/background.ts
var stateByTab = /* @__PURE__ */ new Map();
var API_BASE_URL_KEY = "apiBaseUrl";
var getApiBaseUrl = async () => {
  const stored = await chrome.storage.sync.get(API_BASE_URL_KEY);
  return normalizeApiBaseUrl(
    typeof stored[API_BASE_URL_KEY] === "string" ? stored[API_BASE_URL_KEY] : DEFAULT_API_BASE_URL
  );
};
var setApiBaseUrl = async (apiBaseUrl) => {
  const normalized = normalizeApiBaseUrl(apiBaseUrl);
  await chrome.storage.sync.set({ [API_BASE_URL_KEY]: normalized });
  return normalized;
};
var updateBadge = (tabId, count, verification) => {
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
      tabId
    });
    chrome.action.setBadgeBackgroundColor({
      color,
      tabId
    });
  } catch {
  }
};
var isScanResult = (m) => typeof m === "object" && m !== null && m.type === "vellum:scan-result";
var isGetState = (m) => typeof m === "object" && m !== null && m.type === "vellum:get-state";
var isVerifyText = (m) => typeof m === "object" && m !== null && m.type === "vellum:verify-text";
var isSetApiBaseUrl = (m) => typeof m === "object" && m !== null && m.type === "vellum:set-api-base-url";
var isGetSettings = (m) => typeof m === "object" && m !== null && m.type === "vellum:get-settings";
var markTab = (tabId, verification) => {
  const verified = verification.result.response?.verified === true;
  const reason = verification.result.error ?? verification.result.response?.reason ?? (verified ? "Verified by Vellum" : "Not verified by Vellum");
  try {
    chrome.tabs.sendMessage(tabId, {
      type: "vellum:mark-verified",
      payloadHex: verification.payloadHex,
      verified,
      label: reason
    }).catch?.(() => {
    });
  } catch {
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
        verification: previous?.verification ?? null
      });
      updateBadge(tabId, message.count, previous?.verification ?? null);
    }
    sendResponse({ ok: true });
    return false;
  }
  if (isGetState(message)) {
    const tabId = typeof message.tabId === "number" ? message.tabId : sender.tab?.id;
    const state = typeof tabId === "number" ? stateByTab.get(tabId) ?? null : null;
    sendResponse({ tabId, state });
    return false;
  }
  if (isGetSettings(message)) {
    getApiBaseUrl().then((apiBaseUrl) => sendResponse({ apiBaseUrl }));
    return true;
  }
  if (isSetApiBaseUrl(message)) {
    setApiBaseUrl(message.apiBaseUrl).then(
      (apiBaseUrl) => sendResponse({ apiBaseUrl })
    );
    return true;
  }
  if (isVerifyText(message)) {
    const tabId = message.tabId;
    getApiBaseUrl().then((apiBaseUrl) => verifyText(message.text, apiBaseUrl)).then((result) => {
      const verification = {
        source: message.source,
        textPreview: message.textPreview,
        payloadHex: message.payloadHex,
        result
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
chrome.tabs.onRemoved.addListener((tabId) => {
  stateByTab.delete(tabId);
});
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading" && changeInfo.url) {
    stateByTab.delete(tabId);
    updateBadge(tabId, 0);
  }
});
