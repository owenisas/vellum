/**
 * Visual highlighting layer for detected watermarks.
 *
 * The highlighter wraps each matched range in a `<span class="vellum-detected">`
 * and appends a small badge after the parent block element. CSS is injected once
 * via a `<style id="vellum-style">` tag the first time a highlight is drawn.
 */

import type { WatermarkMeta } from "../shared/payload.js";

export interface HighlightMatch {
  node: Text;
  startIndex: number;
  endIndex: number;
  meta: WatermarkMeta;
}

const STYLE_ID = "vellum-style";
const DETECTED_CLASS = "vellum-detected";
const BADGE_CLASS = "vellum-badge";

const STYLE_CSS = `
.${DETECTED_CLASS} {
  background: rgba(34, 197, 94, 0.18);
  border-bottom: 2px solid rgb(34, 197, 94);
}
.${DETECTED_CLASS}.vellum-verified {
  background: rgba(37, 99, 235, 0.18);
  border-bottom-color: rgb(37, 99, 235);
}
.${DETECTED_CLASS}.vellum-unverified {
  background: rgba(220, 38, 38, 0.14);
  border-bottom-color: rgb(220, 38, 38);
}
.${BADGE_CLASS} {
  display: inline-block;
  margin-left: 4px;
  color: rgb(22, 163, 74);
  font-weight: bold;
}
.${BADGE_CLASS}.vellum-verified {
  color: rgb(37, 99, 235);
}
.${BADGE_CLASS}.vellum-unverified {
  color: rgb(220, 38, 38);
}
`.trim();

export class Highlighter {
  private styleInjected = false;

  /** Wrap each match in a highlight span and emit one badge per parent block. */
  highlight(matches: HighlightMatch[]): void {
    if (matches.length === 0) return;
    this.ensureStyle();

    // Group matches by text node so we can apply ranges in reverse order
    // without invalidating earlier offsets when we split the node.
    const byNode = new Map<Text, HighlightMatch[]>();
    for (const m of matches) {
      const list = byNode.get(m.node);
      if (list) list.push(m);
      else byNode.set(m.node, [m]);
    }

    const badgedParents = new WeakSet<Element>();

    for (const [node, nodeMatches] of byNode.entries()) {
      // Process from end to start so earlier indices stay stable.
      const sorted = [...nodeMatches].sort(
        (a, b) => b.startIndex - a.startIndex,
      );
      // Ensure the node is still attached to the document.
      if (!node.parentNode) continue;

      for (const m of sorted) {
        this.wrapRange(node, m);
      }

      const parent = node.parentElement;
      if (parent && !badgedParents.has(parent)) {
        this.appendBadge(parent);
        badgedParents.add(parent);
      }
    }
  }

  /** Remove every highlight span and badge previously drawn. */
  clear(): void {
    const root = document.body;
    if (!root) return;

    const detected = root.querySelectorAll<HTMLSpanElement>(
      `span.${DETECTED_CLASS}`,
    );
    detected.forEach((span) => {
      const parent = span.parentNode;
      if (!parent) return;
      while (span.firstChild) {
        parent.insertBefore(span.firstChild, span);
      }
      parent.removeChild(span);
      // Merge adjacent text nodes the unwrap may have produced.
      parent.normalize?.();
    });

    const badges = root.querySelectorAll<HTMLSpanElement>(
      `span.${BADGE_CLASS}`,
    );
    badges.forEach((b) => b.remove());
  }

  /** Mark an already-highlighted payload after the backend verifier responds. */
  markVerification(payloadHex: string | undefined, verified: boolean, label: string): void {
    const root = document.body;
    if (!root) return;
    const detected = root.querySelectorAll<HTMLSpanElement>(`span.${DETECTED_CLASS}`);
    detected.forEach((span) => {
      if (payloadHex && span.dataset.payloadHex !== payloadHex) return;
      span.classList.remove("vellum-verified", "vellum-unverified");
      span.classList.add(verified ? "vellum-verified" : "vellum-unverified");
      span.title = label;
      const parent = span.parentElement;
      if (!parent) return;
      const badge = parent.querySelector<HTMLSpanElement>(`span.${BADGE_CLASS}`);
      if (badge) {
        badge.classList.remove("vellum-verified", "vellum-unverified");
        badge.classList.add(verified ? "vellum-verified" : "vellum-unverified");
        badge.textContent = verified ? "Vellum verified" : "Vellum not verified";
        badge.title = label;
      }
    });
  }

  private ensureStyle(): void {
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
  private wrapRange(node: Text, match: HighlightMatch): void {
    const data = node.data;
    if (
      match.startIndex < 0 ||
      match.endIndex > data.length ||
      match.startIndex >= match.endIndex
    ) {
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

  private appendBadge(parent: Element): void {
    const badge = document.createElement("span");
    badge.className = BADGE_CLASS;
    badge.textContent = "Vellum watermark";
    badge.title = "Vellum watermark detected";
    parent.appendChild(badge);
  }
}
