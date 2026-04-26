# Vellum Watermark Detector (Chrome MV3)

A Chrome MV3 extension that scans page text for invisible Unicode watermarks,
then verifies detected or selected text against the Vellum `/api/verify`
endpoint.

## Layout

- `manifest.json` — MV3 manifest.
- `shared/` — codepoint constants, payload codec, popup/background messages, and API client.
- `content/` — content script + DOM scanner + on-page highlighter.
- `background/` — service worker that caches per-tab scan results, calls the verifier, and paints the action badge.
- `popup/` — toolbar popup UI for scanning, endpoint selection, and proof status.
- `icons/` — PNG icons referenced from the manifest.

## Build

The source is `.ts`. A simple `tsc` build emits ES module `.js` files that
Chrome MV3 can load directly.

```sh
npm install
npm run build
```

## Load in Chrome

1. Open `chrome://extensions` and enable **Developer mode**.
2. Click **Load unpacked** and select `extension/dist/`.
3. Open any page; the toolbar icon shows a green badge with the count of
   detected watermarks.
4. Click the extension popup to verify detected text, or select a pasted
   paragraph and click **Verify selection**.

The default verifier endpoint is `https://vellum-387oq.ondigitalocean.app`.
Use the popup selector to switch to the Auth0 demo app or a custom deployment.

## Demo flow

1. Generate and anchor text in the Vellum web app.
2. Paste the watermarked paragraph into a page that preserves zero-width
   characters. `extension/demo/social-post.html` is included as a reliable
   local fallback.
3. Open the extension and click **Scan page**.
4. Click **Verify this text** next to a detected payload. If the platform
   changed the text, select the pasted paragraph and use **Verify selection** to
   show the failure reason.

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
