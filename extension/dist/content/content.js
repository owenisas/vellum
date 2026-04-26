"use strict";
(() => {
  // shared/messages.ts
  var previewText = (text, maxLength = 180) => {
    const compact = text.replace(/\s+/g, " ").trim();
    if (compact.length <= maxLength) return compact;
    return `${compact.slice(0, maxLength - 1)}...`;
  };

  // content/highlighter.ts
  var STYLE_ID = "vellum-style";
  var DETECTED_CLASS = "vellum-detected";
  var BADGE_CLASS = "vellum-badge";
  var STYLE_CSS = `
.${DETECTED_CLASS} {
  background: rgba(125, 211, 252, 0.18) !important;
  outline: 2px solid rgba(125, 211, 252, 0.8) !important;
  outline-offset: 1px;
  border-radius: 3px;
  transition: background 0.15s ease, outline-color 0.15s ease;
}
.${DETECTED_CLASS}.vellum-verified {
  background: rgba(34, 197, 94, 0.22) !important;
  outline-color: rgba(34, 197, 94, 0.95) !important;
}
.${DETECTED_CLASS}.vellum-unverified {
  background: rgba(239, 68, 68, 0.18) !important;
  outline-color: rgba(239, 68, 68, 0.95) !important;
}
.${BADGE_CLASS} {
  display: inline-block;
  margin-left: 6px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(125, 211, 252, 0.65);
  background: rgba(15, 23, 42, 0.92);
  color: rgb(125, 211, 252);
  font: 700 11px/1.2 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.22);
  vertical-align: baseline;
  user-select: none !important;
}
.${BADGE_CLASS}.vellum-verified {
  border-color: rgba(34, 197, 94, 0.75);
  color: rgb(187, 247, 208);
}
.${BADGE_CLASS}.vellum-unverified {
  border-color: rgba(239, 68, 68, 0.75);
  color: rgb(254, 202, 202);
}
`.trim();
  var Highlighter = class {
    styleInjected = false;
    /** Wrap each match in a highlight span and emit one badge per parent block. */
    highlight(matches) {
      if (matches.length === 0) return;
      this.ensureStyle();
      const byNode = /* @__PURE__ */ new Map();
      for (const m of matches) {
        const list = byNode.get(m.node);
        if (list) list.push(m);
        else byNode.set(m.node, [m]);
      }
      const badgedParents = /* @__PURE__ */ new WeakSet();
      for (const [node, nodeMatches] of byNode.entries()) {
        const sorted = [...nodeMatches].sort(
          (a, b) => b.startIndex - a.startIndex
        );
        if (!node.parentNode) continue;
        const parent = node.parentElement;
        for (const m of sorted) {
          this.wrapRange(node, m);
        }
        if (parent && !badgedParents.has(parent)) {
          this.appendBadge(parent);
          badgedParents.add(parent);
        }
      }
    }
    /** Remove every highlight span and badge previously drawn. */
    clear() {
      const root = document.body;
      if (!root) return;
      const detected = root.querySelectorAll(
        `span.${DETECTED_CLASS}`
      );
      detected.forEach((span) => {
        const parent = span.parentNode;
        if (!parent) return;
        while (span.firstChild) {
          parent.insertBefore(span.firstChild, span);
        }
        parent.removeChild(span);
        parent.normalize?.();
      });
      const badges = root.querySelectorAll(
        `span.${BADGE_CLASS}`
      );
      badges.forEach((b) => b.remove());
    }
    /** Mark an already-highlighted payload after the backend verifier responds. */
    markVerification(payloadHex, verified, label) {
      const root = document.body;
      if (!root) return;
      const detected = root.querySelectorAll(`span.${DETECTED_CLASS}`);
      detected.forEach((span) => {
        if (payloadHex && span.dataset.payloadHex !== payloadHex) return;
        span.classList.remove("vellum-verified", "vellum-unverified");
        span.classList.add(verified ? "vellum-verified" : "vellum-unverified");
        span.title = label;
        const parent = span.parentElement;
        if (!parent) return;
        const badge = parent.querySelector(`span.${BADGE_CLASS}`);
        if (badge) {
          badge.classList.remove("vellum-verified", "vellum-unverified");
          badge.classList.add(verified ? "vellum-verified" : "vellum-unverified");
          badge.textContent = verified ? "Vellum verified" : "Vellum not verified";
          badge.title = label;
        }
      });
    }
    ensureStyle() {
      if (this.styleInjected) return;
      if (document.getElementById(STYLE_ID)) {
        this.styleInjected = true;
        return;
      }
      const style = document.createElement("style");
      style.id = STYLE_ID;
      style.textContent = STYLE_CSS;
      (document.head ?? document.documentElement).appendChild(style);
      this.styleInjected = true;
    }
    /**
     * Replace the slice [startIndex, endIndex) of `node` with a wrapping span.
     *
     * After this call, the original `Text` node may have been split; the new
     * span sits between any leading and trailing remainder text nodes.
     */
    wrapRange(node, match) {
      const data = node.data;
      if (match.startIndex < 0 || match.endIndex > data.length || match.startIndex >= match.endIndex) {
        return;
      }
      const parent = node.parentNode;
      if (!parent) return;
      const before = data.slice(0, match.startIndex);
      const middle = data.slice(match.startIndex, match.endIndex);
      const after = data.slice(match.endIndex);
      const span = document.createElement("span");
      span.className = DETECTED_CLASS;
      span.dataset.payloadHex = match.meta.rawPayloadHex;
      span.textContent = middle;
      if (before.length === 0 && after.length === 0) {
        parent.replaceChild(span, node);
        return;
      }
      const fragment = document.createDocumentFragment();
      if (before) fragment.appendChild(document.createTextNode(before));
      fragment.appendChild(span);
      if (after) fragment.appendChild(document.createTextNode(after));
      parent.replaceChild(fragment, node);
    }
    appendBadge(parent) {
      const badge = document.createElement("span");
      badge.className = BADGE_CLASS;
      badge.textContent = "Vellum watermark";
      badge.title = "Vellum watermark detected";
      badge.setAttribute("aria-hidden", "true");
      parent.appendChild(badge);
    }
  };

  // shared/constants.ts
  var TAG_START = "\u2063";
  var TAG_END = "\u2064";
  var ZWSP = "\u200B";
  var ZWNJ = "\u200C";
  var TAG_BITS = 64;

  // shared/payload.ts
  var crc8 = (data) => {
    let crc = 0;
    for (let i = 0; i < data.length; i++) {
      crc ^= data[i] & 255;
      for (let bit = 0; bit < 8; bit++) {
        if ((crc & 128) !== 0) {
          crc = (crc << 1 ^ 7) & 255;
        } else {
          crc = crc << 1 & 255;
        }
      }
    }
    return crc;
  };
  var unpackPayload = (bits) => {
    if (bits.length !== TAG_BITS) {
      throw new Error(
        `unpackPayload: expected ${TAG_BITS} bits, got ${bits.length}`
      );
    }
    if (!/^[01]+$/.test(bits)) {
      throw new Error("unpackPayload: bits must contain only '0' and '1'");
    }
    const payload = BigInt("0b" + bits);
    const schemaVersion = Number(payload >> 60n & 0xfn);
    const issuerId = Number(payload >> 48n & 0xfffn);
    const modelId = Number(payload >> 32n & 0xffffn);
    const modelVersionId = Number(payload >> 16n & 0xffffn);
    const keyId = Number(payload >> 8n & 0xffn);
    const crc = Number(payload & 0xffn);
    const high56 = payload >> 8n;
    const high56Bytes = new Uint8Array(7);
    for (let i = 0; i < 7; i++) {
      const shift = BigInt((6 - i) * 8);
      high56Bytes[i] = Number(high56 >> shift & 0xffn);
    }
    const expectedCrc = crc8(high56Bytes);
    return {
      schemaVersion,
      issuerId,
      modelId,
      modelVersionId,
      keyId,
      crc,
      crcValid: crc === expectedCrc,
      rawPayloadHex: "0x" + payload.toString(16).padStart(16, "0")
    };
  };

  // content/scanner.ts
  var MAX_NODES = 5e3;
  var escapeForRegex = (ch) => ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  var buildTagPattern = () => {
    const start2 = escapeForRegex(TAG_START);
    const end = escapeForRegex(TAG_END);
    const zero = escapeForRegex(ZWSP);
    const one = escapeForRegex(ZWNJ);
    return new RegExp(`${start2}([${zero}${one}]+?)${end}`, "gu");
  };
  var decodeBits = (bitChars) => {
    let out = "";
    for (const c of bitChars) {
      if (c === ZWSP) out += "0";
      else if (c === ZWNJ) out += "1";
    }
    return out;
  };
  var WatermarkScanner = class {
    /** Pre-compiled tag pattern; flags are sticky-free, so `lastIndex` resets per use. */
    pattern = buildTagPattern();
    /** Find every well-formed watermark tag in a single string. */
    scanText(text) {
      if (!text) return [];
      const pattern = new RegExp(this.pattern.source, this.pattern.flags);
      const results = [];
      let match;
      while ((match = pattern.exec(text)) !== null) {
        const bits = decodeBits(match[1]);
        if (bits.length !== TAG_BITS) continue;
        let payload;
        try {
          payload = unpackPayload(bits);
        } catch {
          continue;
        }
        results.push({
          startIndex: match.index,
          endIndex: match.index + match[0].length,
          payload,
          crcValid: payload.crcValid,
          rawBits: bits
        });
      }
      return results;
    }
    /**
     * Walk the DOM beneath `root` and return every watermark found in text nodes.
     *
     * Bounded at {@link MAX_NODES} text nodes to keep pathological pages snappy.
     */
    scan(root = document.body) {
      if (!root) return [];
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      const out = [];
      let visited = 0;
      let current = walker.nextNode();
      while (current !== null && visited < MAX_NODES) {
        visited++;
        const textNode = current;
        const data = textNode.data;
        if (data && data.length > 0) {
          const matches = this.scanText(data);
          for (const m of matches) {
            out.push({ ...m, node: textNode });
          }
        }
        current = walker.nextNode();
      }
      return out;
    }
  };

  // content/content.ts
  var DEBOUNCE_MS = 300;
  var MAX_TEXT_NODES = 5e3;
  var MAX_CANDIDATES = 10;
  var scanner = new WatermarkScanner();
  var highlighter = new Highlighter();
  var observer = null;
  var debounceTimer = null;
  var lastResult = null;
  var lastSelectionText = "";
  var scanInFlight = false;
  var cleanSelectionText = (text) => text.replace(/\s*Vellum (?:watermark|verified|not verified)\s*/g, "").trim();
  var summarize = (meta) => ({
    schemaVersion: meta.schemaVersion,
    issuerId: meta.issuerId,
    modelId: meta.modelId,
    modelVersionId: meta.modelVersionId,
    keyId: meta.keyId,
    crc: meta.crc,
    crcValid: meta.crcValid,
    rawPayloadHex: meta.rawPayloadHex
  });
  var getSelectionText = () => {
    const selected = window.getSelection()?.toString() ?? "";
    const trimmed = cleanSelectionText(selected);
    if (trimmed) lastSelectionText = trimmed;
    return trimmed || lastSelectionText;
  };
  var updateSelectionCache = () => {
    const selected = cleanSelectionText(window.getSelection()?.toString() ?? "");
    if (selected) lastSelectionText = selected;
  };
  var closestTextContainer = (node) => {
    const start2 = node.parentElement;
    return start2?.closest(
      "article, [role='article'], [data-testid='tweetText'], p, li, blockquote, div"
    ) ?? start2;
  };
  var makeCandidate = (textNode, payload, seen) => {
    const container = closestTextContainer(textNode);
    const text = (container?.textContent ?? textNode.data).trim();
    if (!text || seen.has(text)) return null;
    seen.add(text);
    return {
      id: `${payload.rawPayloadHex}:${seen.size}`,
      text,
      preview: previewText(text),
      payload
    };
  };
  var publishResult = (msg) => {
    lastResult = msg;
    try {
      if (typeof chrome !== "undefined" && chrome.runtime?.id) {
        chrome.runtime.sendMessage(msg).catch?.(() => {
        });
      }
    } catch {
    }
  };
  var scanPage = () => {
    if (scanInFlight) {
      return lastResult ?? {
        type: "vellum:scan-result",
        count: 0,
        invalidCount: 0,
        payloads: [],
        candidates: [],
        selectionText: getSelectionText(),
        url: location.href
      };
    }
    scanInFlight = true;
    observer?.disconnect();
    try {
      const selectionText = getSelectionText();
      highlighter.clear();
      const root = document.body;
      const valid = [];
      const summaries = [];
      const candidates = [];
      const candidateTexts = /* @__PURE__ */ new Set();
      let invalidCount = 0;
      if (root) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let visited = 0;
        let current = walker.nextNode();
        while (current !== null && visited < MAX_TEXT_NODES) {
          visited++;
          const textNode = current;
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
                  meta: m.payload
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
      const msg = {
        type: "vellum:scan-result",
        count: valid.length,
        invalidCount,
        payloads: summaries,
        candidates,
        selectionText,
        url: location.href
      };
      publishResult(msg);
      return msg;
    } finally {
      scanInFlight = false;
      attachObserver();
    }
  };
  var scheduleScan = () => {
    if (debounceTimer !== null) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      debounceTimer = null;
      scanPage();
    }, DEBOUNCE_MS);
  };
  var attachObserver = () => {
    if (!document.body) return;
    if (!observer) {
      observer = new MutationObserver((mutations) => {
        for (const mut of mutations) {
          const target = mut.target;
          if (target && target.nodeType === Node.ELEMENT_NODE && (target.classList?.contains("vellum-detected") || target.classList?.contains("vellum-badge"))) {
            continue;
          }
          scheduleScan();
          return;
        }
      });
    }
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  };
  var handleMessage = (message, _sender, sendResponse) => {
    if (typeof message === "object" && message !== null && message.type === "vellum:rescan") {
      const result = scanPage();
      sendResponse(result);
      return true;
    }
    if (typeof message === "object" && message !== null && message.type === "vellum:mark-verified") {
      const m = message;
      highlighter.markVerification(m.payloadHex, m.verified, m.label);
      sendResponse({ ok: true });
      return true;
    }
    return false;
  };
  var start = () => {
    scanPage();
    attachObserver();
    document.addEventListener("selectionchange", updateSelectionCache);
    document.addEventListener("keyup", updateSelectionCache);
    document.addEventListener("mouseup", updateSelectionCache);
    try {
      chrome.runtime.onMessage.addListener(handleMessage);
    } catch {
    }
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
