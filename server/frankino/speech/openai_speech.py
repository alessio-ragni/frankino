"""OpenAI: gpt-4o-transcribe per capire, gpt-4o-mini-tts per parlare (PCM a 24 kHz)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from frankino.config import Settings

VOICE_STYLE = (
    "Parla nella lingua del testo (di solito italiano), con tono caldo e naturale, come un amico di casa. "
    "Ritmo sciolto, niente enfasi da annunciatore."
)


def _client(s: Settings):
    if not s.openai_api_key:
        raise RuntimeError("Manca OPENAI_API_KEY nel .env del server.")
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=s.openai_api_key)


class OpenAITranscriber:
    name = "openai"

    def __init__(self, s: Settings) -> None:
        self.model = s.openai_stt_model
        self.client = _client(s)

    async def transcribe(self, wav: bytes) -> str:
        out = await self.client.audio.transcriptions.create(
            model=self.model,
            file=("voce.wav", wav, "audio/wav"),
            # Lingua riconosciuta da sé (italiano o inglese). Niente suggerimento coi nomi: sul silenzio
            # il trascrittore lo ripete tale e quale, e sembrerebbe un richiamo.
        )
        return (out.text or "").strip()


class OpenAISpeaker:
    name = "openai"
    sample_rate = 24_000

    def __init__(self, s: Settings) -> None:
        self.model = s.openai_tts_model
        self.voice = s.openai_voice
        self.client = _client(s)

    async def speak(self, text: str) -> AsyncIterator[bytes]:
        async with self.client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,
            input=text,
            instructions=VOICE_STYLE,
            response_format="pcm",
        ) as response:
            async for chunk in response.iter_bytes(4800):
                yield chunk
