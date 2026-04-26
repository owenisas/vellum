/**
 * Background service worker. Tracks per-tab scan summaries and handles popup queries.
 */
const tabSummaries = new Map<number, unknown>();

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "scan-summary" && sender.tab?.id !== undefined) {
    tabSummaries.set(sender.tab.id, msg);
    chrome.action.setBadgeText({
      tabId: sender.tab.id,
      text: msg.validCount > 0 ? String(msg.validCount) : "",
    });
    chrome.action.setBadgeBackgroundColor({ color: "#2ea043" });
  }
  if (msg.type === "popup-query" && msg.tabId !== undefined) {
    sendResponse({ summary: tabSummaries.get(msg.tabId) || null });
    return true;
  }
  if (msg.type === "rescan-current") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id !== undefined) chrome.tabs.sendMessage(tabs[0].id, { type: "rescan" });
    });
  }
});

chrome.tabs.onRemoved.addListener((tabId) => tabSummaries.delete(tabId));
