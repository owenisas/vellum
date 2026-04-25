/**
 * Popup controller.
 *
 * Pulls cached scan state from the background service worker, renders the
 * detected watermark list, and wires up the "Scan this page" / "Open dashboard"
 * buttons.
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

interface ScanState {
  count: number;
  invalidCount: number;
  payloads: ScanPayloadSummary[];
  url: string;
  updatedAt: number;
}

interface GetStateResponse {
  tabId: number | undefined;
  state: ScanState | null;
}

interface ScanResultMessage {
  type: "vellum:scan-result";
  count: number;
  invalidCount: number;
  payloads: ScanPayloadSummary[];
  url: string;
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

const requestRescan = async (tabId: number): Promise<ScanState | null> => {
  try {
    const resp = (await chrome.tabs.sendMessage(tabId, {
      type: "vellum:rescan",
    })) as ScanResultMessage | undefined;
    if (!resp) return null;
    return {
      count: resp.count,
      invalidCount: resp.invalidCount,
      payloads: resp.payloads,
      url: resp.url,
      updatedAt: Date.now(),
    };
  } catch {
    return null;
  }
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

const renderState = (state: ScanState | null, url?: string): void => {
  const subtitle = $<HTMLParagraphElement>("#page-url");
  if (subtitle) {
    subtitle.textContent = url ?? state?.url ?? "(no active page)";
  }

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
    const node = template.content.firstElementChild?.cloneNode(true);
    if (!(node instanceof HTMLElement)) continue;

    const setField = (name: string, value: string): void => {
      const el = node.querySelector<HTMLElement>(`[data-field="${name}"]`);
      if (el) el.textContent = value;
    };

    setField("issuerId", String(p.issuerId));
    setField("modelId", `${p.modelId} (v${p.modelVersionId})`);
    setField("keyId", String(p.keyId));
    setField("rawPayloadHex", p.rawPayloadHex);

    const badge = node.querySelector<HTMLElement>('[data-field="crcBadge"]');
    if (badge) {
      badge.textContent = p.crcValid ? "valid" : "invalid";
      badge.classList.add(p.crcValid ? "ok" : "bad");
    }

    list.appendChild(node);
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

  const scanBtn = $<HTMLButtonElement>("#scan-btn");
  scanBtn?.addEventListener("click", async () => {
    scanBtn.disabled = true;
    scanBtn.textContent = "Scanning…";
    const fresh = await requestRescan(tabId);
    renderState(fresh);
    scanBtn.disabled = false;
    scanBtn.textContent = "Scan this page";
  });

  const dashBtn = $<HTMLButtonElement>("#dashboard-btn");
  dashBtn?.addEventListener("click", () => {
    const href = dashBtn.dataset.href;
    if (!href) return;
    try {
      chrome.tabs.create({ url: href });
    } catch {
      window.open(href, "_blank", "noopener");
    }
  });
};

void init();
