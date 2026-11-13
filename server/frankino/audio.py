"""PCM grezzo dal tablet: 16 bit, mono, little-endian. Qui solo il minimo per farne un WAV."""

from __future__ import annotations

import io
import wave

INPUT_RATE = 16_000


def to_wav(pcm: bytes, rate: int = INPUT_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def seconds(pcm: bytes, rate: int = INPUT_RATE) -> float:
    return len(pcm) / 2 / rate
