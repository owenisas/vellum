// shared/api.ts
var DEFAULT_API_BASE_URL = "https://vellum-387oq.ondigitalocean.app";
var KNOWN_API_BASE_URLS = [
  DEFAULT_API_BASE_URL,
  "https://vellum-auth0-ttohk.ondigitalocean.app"
];
var normalizeApiBaseUrl = (value) => {
  const raw = (value ?? DEFAULT_API_BASE_URL).trim().replace(/\/+$/, "");
  if (!raw) return DEFAULT_API_BASE_URL;
  if (!/^https?:\/\//i.test(raw)) return `https://${raw}`;
  return raw;
};

// shared/messages.ts
var previewText = (text, maxLength = 180) => {
  const compact = text.replace(/\s+/g, " ").trim();
  if (compact.length <= maxLength) return compact;
  return `${compact.slice(0, maxLength - 1)}...`;
};

// popup/popup.ts
var $ = (sel) => document.querySelector(sel);
var setStatusPill = (text, tone = "neutral") => {
  const pill = $("#status-pill");
  if (!pill) return;
  pill.className = `status-pill ${tone === "neutral" ? "" : tone}`.trim();
  pill.textContent = text;
};
var setModeInfo = (icon, title, desc) => {
  const iconEl = $("#mode-icon");
  const titleEl = $("#mode-title");
  const descEl = $("#mode-desc");
  if (iconEl) iconEl.textContent = icon;
  if (titleEl) titleEl.textContent = title;
  if (descEl) descEl.textContent = desc;
};
var setActiveAction = (activeId) => {
  for (const id of ["scan-btn", "verify-selection-btn"]) {
    $(`#${id}`)?.classList.toggle("active", id === activeId);
  }
};
var getRequestedTabId = () => {
  const value = new URLSearchParams(location.search).get("tabId");
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
};
var getActiveTabId = async () => {
  const requestedTabId = getRequestedTabId();
  if (requestedTabId !== null) return requestedTabId;
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return typeof tab?.id === "number" ? tab.id : null;
  } catch {
    return null;
  }
};
var fetchState = async (tabId) => {
  try {
    const resp = await chrome.runtime.sendMessage({
      type: "vellum:get-state",
      tabId
    });
    return resp?.state ?? null;
  } catch {
    return null;
  }
};
var fetchSettings = async () => {
  try {
    const resp = await chrome.runtime.sendMessage({
      type: "vellum:get-settings"
    });
    return normalizeApiBaseUrl(resp?.apiBaseUrl);
  } catch {
    return DEFAULT_API_BASE_URL;
  }
};
var saveApiBaseUrl = async (apiBaseUrl) => {
  const resp = await chrome.runtime.sendMessage({
    type: "vellum:set-api-base-url",
    apiBaseUrl
  });
  return normalizeApiBaseUrl(resp.apiBaseUrl);
};
var requestRescan = async (tabId) => {
  try {
    const resp = await chrome.tabs.sendMessage(tabId, {
      type: "vellum:rescan"
    });
    if (!resp) return null;
    return {
      count: resp.count,
      invalidCount: resp.invalidCount,
      payloads: resp.payloads,
      candidates: resp.candidates,
      selectionText: resp.selectionText,
      url: resp.url,
      updatedAt: Date.now(),
      verification: null
    };
  } catch {
    return null;
  }
};
var verifyText = async (tabId, source, text, payloadHex) => {
  const resp = await chrome.runtime.sendMessage({
    type: "vellum:verify-text",
    tabId,
    source,
    text,
    textPreview: previewText(text),
    payloadHex
  });
  return resp?.verification ?? null;
};
var renderEmpty = () => {
  const list = $("#result-list");
  const empty = $("#empty-state");
  const summary = $("#summary");
  if (list) {
    list.hidden = true;
    list.innerHTML = "";
  }
  if (empty) empty.hidden = false;
  if (summary) summary.hidden = true;
};
var escapeHtml = (value) => value.replace(/[&<>"']/g, (ch) => {
  const entities = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  };
  return entities[ch] ?? ch;
});
var field = (label, value) => value === null || value === void 0 || value === "" ? "" : `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(String(value))}</dd>`;
var renderVerification = (verification) => {
  const card = $("#verify-card");
  const status = $("#verify-status");
  const preview = $("#verify-preview");
  const grid = $("#proof-grid");
  if (!card || !status || !preview || !grid) return;
  if (!verification) {
    card.hidden = true;
    return;
  }
  const result = verification.result;
  const response = result.response;
  const verified = response?.verified === true;
  const label = result.error ? "Verifier error" : verified ? "Vellum verified" : "Not verified";
  card.hidden = false;
  status.className = `verify-status ${verified ? "ok" : "bad"}`;
  status.textContent = label;
  setStatusPill(verified ? "Verified" : "Check failed", verified ? "ok" : "bad");
  setModeInfo(
    verified ? "OK" : "!",
    label,
    verified ? "This text hash is anchored in Vellum and matches the selected or detected paragraph." : "The text could not be matched to an anchored Vellum proof. Check that the full signed text was pasted."
  );
  preview.textContent = result.error ?? response?.reason ?? verification.textPreview;
  grid.innerHTML = [
    field("source", verification.source),
    field("company", response?.company),
    field("issuer", response?.issuer_id),
    field("hash", response?.sha256_hash),
    field("tx", response?.tx_hash),
    field("block", response?.block_num),
    field("api", result.apiBaseUrl)
  ].join("");
};
var renderState = (state, url) => {
  const subtitle = $("#page-url");
  if (subtitle) {
    subtitle.textContent = url ?? state?.url ?? "(no active page)";
  }
  renderVerification(state?.verification ?? null);
  if (!state || state.count === 0) {
    renderEmpty();
    if (!state?.verification) {
      setStatusPill(state?.invalidCount ? "Suspicious" : "Ready");
      setModeInfo(
        state?.invalidCount ? "!" : "V",
        state?.invalidCount ? "Hidden data found" : "No watermark yet",
        state?.invalidCount ? "The page contains hidden watermark-like data, but the payload did not pass validation." : "Select a pasted paragraph and use Verify selection, or scan again after pasting Vellum text."
      );
    }
    if (state && state.invalidCount > 0) {
      const summary2 = $("#summary");
      const count = $("#summary-count");
      const label = $(".summary-label");
      const invalid = $("#summary-invalid");
      if (summary2) summary2.hidden = false;
      if (count) count.textContent = "0";
      if (label) label.textContent = "valid watermark(s)";
      if (invalid)
        invalid.textContent = `${state.invalidCount} invalid CRC`;
    }
    return;
  }
  const list = $("#result-list");
  const empty = $("#empty-state");
  const summary = $("#summary");
  const summaryCount = $("#summary-count");
  const summaryInvalid = $("#summary-invalid");
  const template = $("#result-item-template");
  if (!list || !empty || !template) return;
  empty.hidden = true;
  list.hidden = false;
  list.innerHTML = "";
  if (summary) summary.hidden = false;
  if (summaryCount) summaryCount.textContent = String(state.count);
  if (summaryInvalid) {
    summaryInvalid.textContent = state.invalidCount > 0 ? `${state.invalidCount} invalid CRC` : "";
  }
  if (!state.verification) {
    setStatusPill(`${state.count} detected`, "ok");
    setModeInfo(
      "V",
      "Watermark detected",
      "Vellum payloads were found on this page. Verify a detected paragraph to confirm the ledger anchor."
    );
  }
  for (const p of state.payloads) {
    const candidate = state.candidates.find(
      (c) => c.payload.rawPayloadHex === p.rawPayloadHex
    );
    const node = template.content.firstElementChild?.cloneNode(true);
    if (!(node instanceof HTMLElement)) continue;
    const setField = (name, value) => {
      const el = node.querySelector(`[data-field="${name}"]`);
      if (el) el.textContent = value;
    };
    setField("issuerId", String(p.issuerId));
    setField("modelId", `${p.modelId} (v${p.modelVersionId})`);
    setField("rawPayloadHex", p.rawPayloadHex);
    setField("preview", candidate?.preview ?? "Detected watermark payload.");
    const button = node.querySelector(
      '[data-action="verify-candidate"]'
    );
    if (button && candidate) {
      button.addEventListener("click", async () => {
        const tabId = await getActiveTabId();
        if (tabId === null) return;
        setActiveAction(null);
        setStatusPill("Checking");
        setModeInfo(
          "...",
          "Checking detected text",
          "Verifying the highlighted candidate against the configured Vellum endpoint."
        );
        button.disabled = true;
        button.textContent = "Verifying...";
        const verification = await verifyText(
          tabId,
          "candidate",
          candidate.text,
          candidate.payload.rawPayloadHex
        );
        renderVerification(verification);
        button.disabled = false;
        button.textContent = "Verify this text";
      });
    } else if (button) {
      button.disabled = true;
      button.textContent = "No candidate text";
    }
    list.appendChild(node);
  }
};
var applyEndpointUi = (apiBaseUrl) => {
  const select = $("#api-base-url");
  const custom = $("#custom-api-base-url");
  if (!select || !custom) return;
  const normalized = normalizeApiBaseUrl(apiBaseUrl);
  if (KNOWN_API_BASE_URLS.includes(normalized)) {
    select.value = normalized;
    custom.hidden = true;
  } else {
    select.value = "custom";
    custom.hidden = false;
    custom.value = normalized;
  }
};
var init = async () => {
  const tabId = await getActiveTabId();
  if (tabId === null) {
    renderEmpty();
    const subtitle = $("#page-url");
    if (subtitle) subtitle.textContent = "(no active tab)";
    setStatusPill("Unavailable", "bad");
    setModeInfo(
      "!",
      "No active tab",
      "Open a normal web page with pasted Vellum text, then reopen the verifier."
    );
    return;
  }
  const state = await fetchState(tabId);
  renderState(state);
  applyEndpointUi(await fetchSettings());
  const select = $("#api-base-url");
  const custom = $("#custom-api-base-url");
  select?.addEventListener("change", async () => {
    if (select.value === "custom") {
      if (custom) custom.hidden = false;
      setModeInfo(
        "API",
        "Custom endpoint",
        "Enter the Vellum app URL to use for verification requests."
      );
      return;
    }
    const saved = await saveApiBaseUrl(select.value);
    applyEndpointUi(saved);
    setModeInfo("API", "Endpoint saved", `Verification will use ${saved}.`);
  });
  custom?.addEventListener("change", async () => {
    const saved = await saveApiBaseUrl(custom.value);
    applyEndpointUi(saved);
    setModeInfo("API", "Endpoint saved", `Verification will use ${saved}.`);
  });
  const scanBtn = $("#scan-btn");
  scanBtn?.addEventListener("click", async () => {
    setActiveAction("scan-btn");
    setStatusPill("Scanning");
    setModeInfo("...", "Scanning page", "Looking for Vellum zero-width payloads in visible page text.");
    scanBtn.disabled = true;
    scanBtn.textContent = "Scanning...";
    const fresh = await requestRescan(tabId);
    renderState(fresh);
    scanBtn.disabled = false;
    scanBtn.textContent = "Scan this page";
  });
  const selectionBtn = $("#verify-selection-btn");
  selectionBtn?.addEventListener("click", async () => {
    setActiveAction("verify-selection-btn");
    setStatusPill("Checking");
    setModeInfo(
      "...",
      "Checking selection",
      "Reading the selected text from the active tab and asking Vellum to verify its hash."
    );
    selectionBtn.disabled = true;
    selectionBtn.textContent = "Checking...";
    const fresh = await requestRescan(tabId);
    const selection = fresh?.selectionText.trim() ?? "";
    if (!selection) {
      renderVerification({
        source: "selection",
        textPreview: "No selected text on the active page.",
        result: {
          ok: false,
          apiBaseUrl: await fetchSettings(),
          checkedAt: Date.now(),
          error: "Select the pasted paragraph on the page, then click Verify selection."
        }
      });
    } else {
      const verification = await verifyText(tabId, "selection", selection);
      renderVerification(verification);
    }
    selectionBtn.disabled = false;
    selectionBtn.textContent = "Verify selection";
  });
};
void init();
