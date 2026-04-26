import { WatermarkHighlighter } from "./highlighter";
import { WatermarkScanner } from "./scanner";

const scanner = new WatermarkScanner();
const highlighter = new WatermarkHighlighter();

function scan() {
  if (!document.body) return;
  const results = scanner.scan(document.body);
  highlighter.highlight(results);
  // Send a summary to the background worker for popup queries.
  const valid = results.filter((r) => r.payload?.codeValid).length;
  chrome.runtime.sendMessage({
    type: "scan-summary",
    url: location.href,
    tagCount: results.length,
    validCount: valid,
    payloads: results.filter((r) => r.payload).map((r) => r.payload),
  }).catch(() => {});
}

let scheduled = false;
function scheduleScan() {
  if (scheduled) return;
  scheduled = true;
  setTimeout(() => {
    scheduled = false;
    scan();
  }, 250);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", scheduleScan);
} else {
  scheduleScan();
}

const observer = new MutationObserver(() => scheduleScan());
observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "rescan") {
    scan();
    sendResponse({ ok: true });
  }
});
