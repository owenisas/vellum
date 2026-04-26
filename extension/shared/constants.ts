export const TAG_START = "⁣";   // INVISIBLE SEPARATOR
export const TAG_END   = "⁤";   // INVISIBLE PLUS
export const ZWSP      = "​";   // ZERO-WIDTH SPACE → 0
export const ZWNJ      = "‌";   // ZERO-WIDTH NON-JOINER → 1
export const TAG_BITS = 64;
export const SCAN_TIMEOUT_MS = 5000;
export const TAG_TOTAL_LEN = TAG_START.length + TAG_BITS + TAG_END.length;
