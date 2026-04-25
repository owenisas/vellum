# Vellum Watermark Detector (Chrome MV3)

A Chrome MV3 extension that scans page text for invisible Unicode watermarks
written in the Vellum zero-width format and surfaces issuer, model, and key
metadata.

## Layout

- `manifest.json` — MV3 manifest.
- `shared/` — codepoint constants and the 64-bit payload codec (CRC-8 poly 0x07).
- `content/` — content script + DOM scanner + on-page highlighter.
- `background/` — service worker that caches per-tab scan results and paints the action badge.
- `popup/` — toolbar popup UI.
- `icons/` — referenced from the manifest. PNGs not generated here.

## Build

The source is `.ts`. A simple `tsc` build emits ES module `.js` files that
Chrome MV3 can load directly.

```sh
npm install
npm run build
```

## Load in Chrome

1. Open `chrome://extensions` and enable **Developer mode**.
2. Click **Load unpacked** and select either:
   - `extension/dist/` — after running `npm run build`, recommended, or
   - `extension/` — works once `dist/` is built and the manifest path is consistent.
3. Open any page; the toolbar icon shows a green badge with the count of
   detected watermarks.

## Wire format

64-bit MSB-first payload:

| bits     | field              | width |
| -------- | ------------------ | ----- |
| `[63:60]`| `schema_version`   | 4     |
| `[59:48]`| `issuer_id`        | 12    |
| `[47:32]`| `model_id`         | 16    |
| `[31:16]`| `model_version_id` | 16    |
| `[15:8]` | `key_id`           | 8     |
| `[7:0]`  | `crc8` (poly 0x07) | 8     |

Encoded between `U+2063` (start) / `U+2064` (end) using `U+200B` for bit `0`
and `U+200C` for bit `1`.
