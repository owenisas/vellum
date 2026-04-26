// Bundle TS entry points + copy manifest/static assets.
import * as esbuild from "esbuild";
import { cpSync, mkdirSync, existsSync } from "node:fs";

const OUT = "dist";
mkdirSync(OUT, { recursive: true });
mkdirSync(`${OUT}/content`, { recursive: true });
mkdirSync(`${OUT}/background`, { recursive: true });
mkdirSync(`${OUT}/popup`, { recursive: true });
mkdirSync(`${OUT}/icons`, { recursive: true });

await esbuild.build({
  entryPoints: ["content/content.ts", "background/background.ts", "popup/popup.ts"],
  bundle: true,
  format: "esm",
  outdir: OUT,
  target: ["chrome120"],
});

cpSync("manifest.json", `${OUT}/manifest.json`);
cpSync("popup/popup.html", `${OUT}/popup/popup.html`);
cpSync("popup/popup.css", `${OUT}/popup/popup.css`);
if (existsSync("icons")) cpSync("icons", `${OUT}/icons`, { recursive: true });

console.log("Extension built →", OUT);
