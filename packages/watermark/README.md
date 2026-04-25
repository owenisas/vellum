# vellum-watermark

Pure-Python library for embedding and detecting invisible Unicode watermarks in
AI-generated text. Zero dependencies.

## Usage

```python
from watermark import Watermarker

wm = Watermarker(issuer_id=42, model_id=1001, model_version_id=1, key_id=1)
tagged = wm.apply("Some long generated text " * 30)

result = wm.detect(tagged)
assert result.watermarked
assert result.valid_count > 0
```

## Payload Format (64 bits)

```
[63:60] schema_version  4 bits
[59:48] issuer_id      12 bits
[47:32] model_id       16 bits
[31:16] model_version  16 bits
[15:8 ] key_id          8 bits
[ 7:0 ] crc8            8 bits  CRC-8 over high 56 bits, polynomial 0x07
```

Bits are encoded as zero-width characters (`U+200B` for 0, `U+200C` for 1) wrapped between
invisible separators (`U+2063` start, `U+2064` end).
