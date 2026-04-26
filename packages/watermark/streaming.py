"""
Streaming TagInjector for incremental watermarking during LLM token streaming.
"""

from __future__ import annotations

from .zero_width import (
    InjectionMode,
    encode_bits,
    split_for_injection,
)


class TagInjector:
    """
    Inject watermark tags into text incrementally as it streams in.

    Usage:
        injector = TagInjector(tag_bits, repeat_interval=160, mode="whitespace")
        for chunk in llm_stream:
            yield injector.inject_delta(chunk)
        yield injector.finalize()
    """

    def __init__(
        self,
        tag_bits: str,
        *,
        repeat_interval: int = 160,
        mode: InjectionMode = InjectionMode.WHITESPACE,
        force_minimum: int = 20,
    ) -> None:
        self._tag = encode_bits(tag_bits)
        self._tag_bits = tag_bits
        self._repeat_interval = repeat_interval
        self._mode = mode
        self._force_minimum = force_minimum
        self._token_count = 0
        self._tags_inserted = 0
        self._buffer = ""
        self._all_text = ""

    def inject_delta(self, chunk: str, *, finalize: bool = False) -> str:
        """Process a chunk; return what should be emitted to the consumer now.

        Note: force-tag fallback for short text is the caller's responsibility
        (see Watermarker.apply). Streaming sees only one chunk at a time and
        cannot position a tag at "40% of the full output" because the full
        output isn't known yet.
        """
        self._buffer += chunk
        self._all_text += chunk
        if finalize:
            emit = self._buffer
            self._buffer = ""
        else:
            ws_idx = max(self._buffer.rfind(" "), self._buffer.rfind("\n"))
            if ws_idx < 0:
                return ""
            emit = self._buffer[: ws_idx + 1]
            self._buffer = self._buffer[ws_idx + 1 :]

        return self._inject_into(emit)

    def finalize(self) -> str:
        return self.inject_delta("", finalize=True)

    def _inject_into(self, text: str) -> str:
        spans = split_for_injection(text, self._mode)
        if not spans:
            return text
        out_chars: list[str] = []
        cursor = 0
        for _, end in spans:
            out_chars.append(text[cursor:end])
            cursor = end
            self._token_count += 1
            if self._token_count % self._repeat_interval == 0:
                out_chars.append(self._tag)
                self._tags_inserted += 1
        out_chars.append(text[cursor:])
        return "".join(out_chars)

    def _maybe_force(self, finalized: str) -> str:
        if self._tags_inserted > 0 or len(self._all_text) <= self._force_minimum:
            return finalized
        # Inject one tag at ~40% of length.
        pos = max(1, int(len(finalized) * 0.4))
        # Snap to next whitespace if any.
        ws = finalized.find(" ", pos)
        if ws != -1 and ws - pos < 50:
            pos = ws + 1
        forced = finalized[:pos] + self._tag + finalized[pos:]
        self._tags_inserted += 1
        return forced
