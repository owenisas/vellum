/**
 * Zero-width Unicode codepoints used by the Vellum watermark format.
 *
 * Mirrors the canonical configuration in `packages/watermark/config.py`:
 *   tag_start = U+2063 (INVISIBLE SEPARATOR)
 *   tag_end   = U+2064 (INVISIBLE PLUS)
 *   bit_zero  = U+200B (ZERO WIDTH SPACE)
 *   bit_one   = U+200C (ZERO WIDTH NON-JOINER)
 *
 * Codepoints are written as `\u{...}` escapes so this file is ASCII-safe.
 */

export const TAG_START = "\u{2063}";
export const TAG_END = "\u{2064}";
export const ZWSP = "\u{200B}";
export const ZWNJ = "\u{200C}";

/** Number of bits encoded between TAG_START and TAG_END. */
export const TAG_BITS = 64;
