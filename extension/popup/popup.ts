import {
  DEFAULT_API_BASE_URL,
  KNOWN_API_BASE_URLS,
  normalizeApiBaseUrl,
} from "../shared/api.js";
import type {
  CandidateText,
  RuntimeMessage,
  ScanResultMessage,
  ScanState,
  VerificationState,
} from "../shared/messages.js";
import { previewText } from "../shared/messages.js";

interface GetStateResponse {
  tabId: number | undefined;
  state: ScanState | null;
}

const $ = <T extends Element = HTMLElement>(sel: string): T | null =>
  document.querySelector<T>(sel);

const getActiveTabId = async (): Promise<number | null> => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return typeof tab?.id === "number" ? tab.id : null;
  } catch {
    return null;
  }
};

const fetchState = async (tabId: number): Promise<ScanState | null> => {
  try {
    const resp = (await chrome.runtime.sendMessage({
      type: "vellum:get-state",
      tabId,
    })) as GetStateResponse | undefined;
    return resp?.state ?? null;
  } catch {
    return null;
  }
};

const fetchSettings = async (): Promise<string> => {
  try {
    const resp = (await chrome.runtime.sendMessage({
      type: "vellum:get-settings",
    } satisfies RuntimeMessage)) as { apiBaseUrl?: string } | undefined;
    return normalizeApiBaseUrl(resp?.apiBaseUrl);
  } catch {
    return DEFAULT_API_BASE_URL;
  }
};

const saveApiBaseUrl = async (apiBaseUrl: string): Promise<string> => {
  const resp = (await chrome.runtime.sendMessage({
    type: "vellum:set-api-base-url",
    apiBaseUrl,
  } satisfies RuntimeMessage)) as { apiBaseUrl: string };
  return normalizeApiBaseUrl(resp.apiBaseUrl);
};

const requestRescan = async (tabId: number): Promise<ScanState | null> => {
  try {
    const resp = (await chrome.tabs.sendMessage(tabId, {
      type: "vellum:rescan",
    } satisfies RuntimeMessage)) as ScanResultMessage | undefined;
    if (!resp) return null;
    return {
      count: resp.count,
      invalidCount: resp.invalidCount,
      payloads: resp.payloads,
      candidates: resp.candidates,
      selectionText: resp.selectionText,
      url: resp.url,
      updatedAt: Date.now(),
      verification: null,
    };
  } catch {
    return null;
  }
};

const verifyText = async (
  tabId: number,
  source: "selection" | "candidate",
  text: string,
  payloadHex?: string,
): Promise<VerificationState | null> => {
  const resp = (await chrome.runtime.sendMessage({
    type: "vellum:verify-text",
    tabId,
    source,
    text,
    textPreview: previewText(text),
    payloadHex,
  } satisfies RuntimeMessage)) as { verification?: VerificationState } | undefined;
  return resp?.verification ?? null;
};

const renderEmpty = (): void => {
  const list = $<HTMLUListElement>("#result-list");
  const empty = $<HTMLParagraphElement>("#empty-state");
  const summary = $<HTMLElement>("#summary");
  if (list) {
    list.hidden = true;
    list.innerHTML = "";
  }
  if (empty) empty.hidden = false;
  if (summary) summary.hidden = true;
};

const escapeHtml = (value: string): string =>
  value.replace(/[&<>"']/g, (ch) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[ch] ?? ch;
  });

const field = (label: string, value: string | number | null | undefined): string =>
  value === null || value === undefined || value === ""
    ? ""
    : `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(String(value))}</dd>`;

const renderVerification = (verification: VerificationState | null): void => {
  const card = $<HTMLElement>("#verify-card");
  const status = $<HTMLElement>("#verify-status");
  const preview = $<HTMLParagraphElement>("#verify-preview");
  const grid = $<HTMLElement>("#proof-grid");
  if (!card || !status || !preview || !grid) return;

  if (!verification) {
    card.hidden = true;
    return;
  }

  const result = verification.result;
  const response = result.response;
  const verified = response?.verified === true;
  const label = result.error
    ? "Verifier error"
    : verified
      ? "Vellum verified"
      : "Not verified";

  card.hidden = false;
  status.className = `verify-status ${verified ? "ok" : "bad"}`;
  status.textContent = label;
  preview.textContent =
    result.error ?? response?.reason ?? verification.textPreview;
  grid.innerHTML = [
    field("source", verification.source),
    field("company", response?.company),
    field("issuer", response?.issuer_id),
    field("hash", response?.sha256_hash),
    field("tx", response?.tx_hash),
    field("block", response?.block_num),
    field("api", result.apiBaseUrl),
  ].join("");
};

const renderState = (state: ScanState | null, url?: string): void => {
  const subtitle = $<HTMLParagraphElement>("#page-url");
  if (subtitle) {
    subtitle.textContent = url ?? state?.url ?? "(no active page)";
  }

  renderVerification(state?.verification ?? null);

  if (!state || state.count === 0) {
    renderEmpty();
    if (state && state.invalidCount > 0) {
      const summary = $<HTMLElement>("#summary");
      const count = $<HTMLElement>("#summary-count");
      const label = $<HTMLElement>(".summary-label");
      const invalid = $<HTMLElement>("#summary-invalid");
      if (summary) summary.hidden = false;
      if (count) count.textContent = "0";
      if (label) label.textContent = "valid watermark(s)";
      if (invalid)
        invalid.textContent = `${state.invalidCount} invalid CRC`;
    }
    return;
  }

  const list = $<HTMLUListElement>("#result-list");
  const empty = $<HTMLParagraphElement>("#empty-state");
  const summary = $<HTMLElement>("#summary");
  const summaryCount = $<HTMLElement>("#summary-count");
  const summaryInvalid = $<HTMLElement>("#summary-invalid");
  const template = $<HTMLTemplateElement>("#result-item-template");

  if (!list || !empty || !template) return;

  empty.hidden = true;
  list.hidden = false;
  list.innerHTML = "";

  if (summary) summary.hidden = false;
  if (summaryCount) summaryCount.textContent = String(state.count);
  if (summaryInvalid) {
    summaryInvalid.textContent =
      state.invalidCount > 0 ? `${state.invalidCount} invalid CRC` : "";
  }

  for (const p of state.payloads) {
    const candidate = state.candidates.find(
      (c) => c.payload.rawPayloadHex === p.rawPayloadHex,
    );
    const node = template.content.firstElementChild?.cloneNode(true);
    if (!(node instanceof HTMLElement)) continue;

    const setField = (name: string, value: string): void => {
      const el = node.querySelector<HTMLElement>(`[data-field="${name}"]`);
      if (el) el.textContent = value;
    };

    setField("issuerId", String(p.issuerId));
    setField("modelId", `${p.modelId} (v${p.modelVersionId})`);
    setField("rawPayloadHex", p.rawPayloadHex);
    setField("preview", candidate?.preview ?? "Detected watermark payload.");

    const button = node.querySelector<HTMLButtonElement>(
      '[data-action="verify-candidate"]',
    );
    if (button && candidate) {
      button.addEventListener("click", async () => {
        const tabId = await getActiveTabId();
        if (tabId === null) return;
        button.disabled = true;
        button.textContent = "Verifying...";
        const verification = await verifyText(
          tabId,
          "candidate",
          candidate.text,
          candidate.payload.rawPayloadHex,
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

const applyEndpointUi = (apiBaseUrl: string): void => {
  const select = $<HTMLSelectElement>("#api-base-url");
  const custom = $<HTMLInputElement>("#custom-api-base-url");
  if (!select || !custom) return;
  const normalized = normalizeApiBaseUrl(apiBaseUrl);
  if ((KNOWN_API_BASE_URLS as readonly string[]).includes(normalized)) {
    select.value = normalized;
    custom.hidden = true;
  } else {
    select.value = "custom";
    custom.hidden = false;
    custom.value = normalized;
  }
};

const init = async (): Promise<void> => {
  const tabId = await getActiveTabId();
  if (tabId === null) {
    renderEmpty();
    const subtitle = $<HTMLParagraphElement>("#page-url");
    if (subtitle) subtitle.textContent = "(no active tab)";
    return;
  }

  const state = await fetchState(tabId);
  renderState(state);
  applyEndpointUi(await fetchSettings());

  const select = $<HTMLSelectElement>("#api-base-url");
  const custom = $<HTMLInputElement>("#custom-api-base-url");
  select?.addEventListener("change", async () => {
    if (select.value === "custom") {
      if (custom) custom.hidden = false;
      return;
    }
    const saved = await saveApiBaseUrl(select.value);
    applyEndpointUi(saved);
  });
  custom?.addEventListener("change", async () => {
    const saved = await saveApiBaseUrl(custom.value);
    applyEndpointUi(saved);
  });

  const scanBtn = $<HTMLButtonElement>("#scan-btn");
  scanBtn?.addEventListener("click", async () => {
    scanBtn.disabled = true;
    scanBtn.textContent = "Scanning…";
    const fresh = await requestRescan(tabId);
    renderState(fresh);
    scanBtn.disabled = false;
    scanBtn.textContent = "Scan this page";
  });

  const selectionBtn = $<HTMLButtonElement>("#verify-selection-btn");
  selectionBtn?.addEventListener("click", async () => {
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
          error: "Select the pasted paragraph on the page, then click Verify selection.",
        },
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
