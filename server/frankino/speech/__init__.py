"""Capire e parlare. Anthropic non fa né l'una né l'altra cosa, quindi si appoggia fuori.

Due cose sole, sempre uguali per qualunque servizio:

* `Transcriber.transcribe(wav) -> testo`
* `Speaker.speak(testo) -> pezzi di PCM 16 bit mono a `sample_rate``

Il servizio si sceglie dal `.env` (`FRANKINO_STT`, `FRANKINO_TTS`). Per
aggiungerne uno: un file in questa cartella e una riga nei due dizionari.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Protocol

from frankino.config import Settings


class Transcriber(Protocol):
    name: str

    async def transcribe(self, wav: bytes) -> str: ...


class Speaker(Protocol):
    name: str
    sample_rate: int

    def speak(self, text: str) -> AsyncIterator[bytes]: ...


def _openai_stt(s: Settings) -> Transcriber:
    from .openai_speech import OpenAITranscriber

    return OpenAITranscriber(s)


def _openai_tts(s: Settings) -> Speaker:
    from .openai_speech import OpenAISpeaker

    return OpenAISpeaker(s)


def _eleven_stt(s: Settings) -> Transcriber:
    from .elevenlabs_speech import ElevenLabsTranscriber

    return ElevenLabsTranscriber(s)


def _eleven_tts(s: Settings) -> Speaker:
    from .elevenlabs_speech import ElevenLabsSpeaker

    return ElevenLabsSpeaker(s)


TRANSCRIBERS: dict[str, Callable[[Settings], Transcriber]] = {
    "openai": _openai_stt,
    "elevenlabs": _eleven_stt,
}
SPEAKERS: dict[str, Callable[[Settings], Speaker]] = {
    "openai": _openai_tts,
    "elevenlabs": _eleven_tts,
}


def transcriber(s: Settings) -> Transcriber:
    if s.stt not in TRANSCRIBERS:
        raise ValueError(f"FRANKINO_STT={s.stt!r}: scegli fra {', '.join(TRANSCRIBERS)}")
    return TRANSCRIBERS[s.stt](s)


def speaker(s: Settings) -> Speaker:
    if s.tts not in SPEAKERS:
        raise ValueError(f"FRANKINO_TTS={s.tts!r}: scegli fra {', '.join(SPEAKERS)}")
    return SPEAKERS[s.tts](s)
