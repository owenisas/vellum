import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const OUT = resolve(process.cwd(), "snaps");
mkdirSync(OUT, { recursive: true });

const PAGES = [
  { name: "cover-laptop",      url: "/",            w: 1440, h: 900,  full: true },
  { name: "cover-mobile",      url: "/",            w: 390,  h: 844,  full: true },
  { name: "studio-laptop",     url: "/studio",      w: 1440, h: 900,  full: true },
  { name: "studio-mobile",     url: "/studio",      w: 390,  h: 844,  full: true },
  { name: "ledger-laptop",     url: "/ledger",      w: 1440, h: 900,  full: true },
  { name: "principles-laptop", url: "/principles",  w: 1440, h: 900,  full: true },
];

const BASE = process.env.BASE || "http://localhost:5173";

const browser = await chromium.launch();
const context = await browser.newContext({ deviceScaleFactor: 2 });
context.setDefaultTimeout(15000);
const page = await context.newPage();
page.on("console", (m) => {
  if (m.type() === "error" || m.type() === "warning") {
    console.log(`  [${m.type()}]`, m.text());
  }
});
page.on("pageerror", (e) => console.log("  [pageerror]", e.message));

for (const p of PAGES) {
  await page.setViewportSize({ width: p.w, height: p.h });
  console.log(`→ ${p.url}  ${p.w}x${p.h}`);
  await page.goto(`${BASE}${p.url}`, { waitUntil: "networkidle" });
  // give animations enough time to fully resolve (display-heading staggers up to ~1.6s)
  await page.waitForTimeout(2400);
  const file = `${OUT}/${p.name}.png`;
  await page.screenshot({ path: file, fullPage: !!p.full });
  console.log(`  saved ${file}`);
}

await browser.close();
console.log("done");
