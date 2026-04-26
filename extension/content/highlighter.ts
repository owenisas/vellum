import { ScanResult } from "./scanner";

const STYLE_ID = "veritext-style";

function injectStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .veritext-detected { background: rgba(46,160,67,0.15); border-bottom: 1px dotted #2ea043; }
    .veritext-badge {
      position: fixed; top: 16px; right: 16px; z-index: 2147483647;
      background: #161b22; color: #2ea043; border: 1px solid #2ea043;
      border-radius: 6px; padding: 6px 10px; font: 12px ui-monospace, monospace;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }
  `;
  document.head.appendChild(style);
}

export class WatermarkHighlighter {
  private badge: HTMLDivElement | null = null;

  highlight(results: ScanResult[]): void {
    injectStyle();
    if (!results.length) return;
    const valid = results.filter((r) => r.payload?.codeValid);
    if (valid.length) {
      this.showBadge(`✓ Veritext: ${valid.length} tag${valid.length === 1 ? "" : "s"}`);
    }
  }

  showBadge(text: string) {
    if (this.badge) this.badge.remove();
    this.badge = document.createElement("div");
    this.badge.className = "veritext-badge";
    this.badge.textContent = text;
    document.body.appendChild(this.badge);
    setTimeout(() => this.badge?.remove(), 8000);
  }

  clearHighlights() {
    document.querySelectorAll(".veritext-detected").forEach((el) => el.remove());
    this.badge?.remove();
    this.badge = null;
  }
}
