"""Tutta la configurazione arriva dall'ambiente (o da `.env`). Niente valori cablati."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str
    port: int
    token: str
    model: str
    tz: str
    stt: str
    tts: str
    openai_api_key: str
    openai_stt_model: str
    openai_tts_model: str
    openai_voice: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    elevenlabs_stt_model: str
    elevenlabs_tts_model: str
    audio_days: int
    a2ui_version: str
    confirm_timeout_s: float

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> Settings:
        load_dotenv(env_file or Path.cwd() / ".env")
        return cls(
            data_dir=Path(_get("FRANKINO_DATA", str(Path.home() / ".frankino"))).expanduser(),
            host=_get("FRANKINO_HOST", "0.0.0.0"),
            port=int(_get("FRANKINO_PORT", "4390")),
            token=_get("FRANKINO_TOKEN"),
            model=_get("FRANKINO_MODEL", "claude-sonnet-5-5"),
            tz=_get("FRANKINO_TZ", "Europe/Rome"),
            stt=_get("FRANKINO_STT", "openai"),
            tts=_get("FRANKINO_TTS", "openai"),
            openai_api_key=_get("OPENAI_API_KEY"),
            openai_stt_model=_get("FRANKINO_OPENAI_STT_MODEL", "gpt-4o-transcribe"),
            openai_tts_model=_get("FRANKINO_OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            openai_voice=_get("FRANKINO_OPENAI_VOICE", "ash"),
            elevenlabs_api_key=_get("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=_get("FRANKINO_ELEVENLABS_VOICE_ID"),
            elevenlabs_stt_model=_get("FRANKINO_ELEVENLABS_STT_MODEL", "scribe_v1"),
            elevenlabs_tts_model=_get("FRANKINO_ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5"),
            audio_days=int(_get("FRANKINO_AUDIO_DAYS", "30")),
            a2ui_version=_get("FRANKINO_A2UI_VERSION", "v0.9.1"),
            confirm_timeout_s=float(_get("FRANKINO_CONFIRM_TIMEOUT_S", "120")),
        )

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "frankino.db"

    @property
    def work_dir(self) -> Path:
        """La cartella in cui gira Claude: vuota, sua, lontana dai file di chi lo ospita."""
        return self.data_dir / "lavoro"
