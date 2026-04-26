interface PayloadView {
  schemaVersion: number;
  issuerId: number;
  modelId: number;
  modelVersionId: number;
  keyId: number;
  codeValid: boolean;
  errorsCorrected: number;
}

async function load() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tabId = tabs[0]?.id;
  if (tabId === undefined) return;
  const resp = await chrome.runtime.sendMessage({ type: "popup-query", tabId });
  const summary = resp?.summary;
  const status = document.getElementById("status")!;
  const results = document.getElementById("results")!;
  if (!summary) {
    status.textContent = "No tags detected on this page.";
    return;
  }
  status.innerHTML = `Tags: <strong>${summary.tagCount}</strong> · Valid: <span class="ok">${summary.validCount}</span>`;
  results.innerHTML = "";
  for (const p of summary.payloads as PayloadView[]) {
    const div = document.createElement("div");
    div.className = "result";
    div.innerHTML = `
      <div>Issuer: <strong>${p.issuerId}</strong> · Model: ${p.modelId} v${p.modelVersionId}</div>
      <div>Status: <span class="${p.codeValid ? "ok" : "warn"}">
        ${p.codeValid ? `valid (corrected ${p.errorsCorrected})` : "invalid"}
      </span></div>
    `;
    results.appendChild(div);
  }
}

document.getElementById("rescan")?.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "rescan-current" });
  setTimeout(load, 500);
});

load();
