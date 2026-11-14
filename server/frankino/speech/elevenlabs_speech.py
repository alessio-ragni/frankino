"""ElevenLabs: Scribe per capire, la voce in streaming (PCM a 24 kHz) per parlare.

Si accende con `FRANKINO_STT=elevenlabs` e/o `FRANKINO_TTS=elevenlabs`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from frankino.config import Settings

BASE = "https://api.elevenlabs.io/v1"


def _headers(s: Settings) -> dict[str, str]:
    if not s.elevenlabs_api_key:
        raise RuntimeError("Manca ELEVENLABS_API_KEY nel .env del server.")
    return {"xi-api-key": s.elevenlabs_api_key}


class ElevenLabsTranscriber:
    name = "elevenlabs"

    def __init__(self, s: Settings) -> None:
        self.headers = _headers(s)
        self.model = s.elevenlabs_stt_model

    async def transcribe(self, wav: bytes) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{BASE}/speech-to-text",
                headers=self.headers,
                data={"model_id": self.model},  # lingua riconosciuta da sé
                files={"file": ("voce.wav", wav, "audio/wav")},
            )
            r.raise_for_status()
            return str(r.json().get("text", "")).strip()


class ElevenLabsSpeaker:
    name = "elevenlabs"
    sample_rate = 24_000

    def __init__(self, s: Settings) -> None:
        self.headers = _headers(s)
        if not s.elevenlabs_voice_id:
            raise RuntimeError("Manca FRANKINO_ELEVENLABS_VOICE_ID nel .env del server.")
        self.voice = s.elevenlabs_voice_id
        self.model = s.elevenlabs_tts_model

    async def speak(self, text: str) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{BASE}/text-to-speech/{self.voice}/stream",
                params={"output_format": "pcm_24000"},
                headers=self.headers,
                json={"text": text, "model_id": self.model},
            ) as r:
                r.raise_for_status()
                async for chunk in r.aiter_bytes(4800):
                    yield chunk
