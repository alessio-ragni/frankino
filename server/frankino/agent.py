"""Il cervello: Claude Code, attraverso l'Agent SDK, con il login dell'abbonamento.

Gira con le impostazioni utente di chi lo ospita, così vede i suoi stessi
connettori (claude.ai e MCP), ma con gli hook spenti e in una cartella vuota
sua. Degli strumenti di serie restano solo cercare sul web e leggere una
pagina: niente shell, niente file.

Una conversazione per dispositivo collegato: il filo lo tiene il client.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from frankino.config import Settings

log = logging.getLogger("frankino.agent")

PROMPT = Path(__file__).parent / "prompts" / "carattere.md"

_DAYS = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]


def system_prompt(s: Settings) -> str:
    return PROMPT.read_text(encoding="utf-8").format(a2ui_version=s.a2ui_version)


def when(s: Settings, now: datetime | None = None) -> str:
    t = now or datetime.now(ZoneInfo(s.tz))
    return f"{_DAYS[t.weekday()]} {t:%d/%m/%Y}, ore {t:%H:%M}"


class Agent:
    def __init__(self, s: Settings, screen, gate) -> None:
        self.s = s
        self.screen = screen
        self.gate = gate
        self.client = None

    async def start(self) -> None:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

        if os.environ.get("ANTHROPIC_API_KEY"):
            log.warning("ANTHROPIC_API_KEY è impostata: la CLI userà la chiave, non l'abbonamento.")
        self.s.work_dir.mkdir(parents=True, exist_ok=True)
        options = ClaudeAgentOptions(
            system_prompt=system_prompt(self.s),
            model=self.s.model,
            effort=self.s.effort or None,
            tools=["WebSearch", "WebFetch"],
            mcp_servers={"schermo": self.screen},
            setting_sources=["user"],
            settings='{"disableAllHooks": true}',
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[self.gate.pre_tool_use])]},
            include_partial_messages=True,
            cwd=str(self.s.work_dir),
            # Le conversazioni non si salvano su disco: Frankino non le riprende, e così quello
            # che si dice in casa non resta nei file di Claude Code.
            extra_args={"no-session-persistence": None},
        )
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()

    async def stop(self) -> None:
        if self.client is not None:
            await self.client.disconnect()
            self.client = None

    async def interrupt(self) -> None:
        if self.client is not None:
            await self.client.interrupt()

    async def ask(self, text: str, on_text: Callable[[str], None]) -> str:
        """Manda la frase a Claude e passa i pezzi di risposta a `on_text` man mano."""
        from claude_agent_sdk import AssistantMessage, StreamEvent, TextBlock

        assert self.client is not None, "start() prima di ask()"
        await self.client.query(f"[{when(self.s)}] {text}")
        streamed: list[str] = []
        whole: list[str] = []
        async for message in self.client.receive_response():
            if isinstance(message, StreamEvent):
                ev = message.event
                if ev.get("type") == "content_block_start" and streamed:
                    # Un nuovo blocco di testo dopo uno strumento: è un'altra frase.
                    if ev.get("content_block", {}).get("type") == "text":
                        on_text("\n")
                elif ev.get("type") == "content_block_delta":
                    delta = ev.get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        streamed.append(delta["text"])
                        on_text(delta["text"])
            elif isinstance(message, AssistantMessage):
                whole.extend(b.text for b in message.content if isinstance(b, TextBlock))
        if not streamed and whole:
            # Nessun pezzo in streaming (capita): si dice tutto alla fine.
            for piece in whole:
                on_text(piece + "\n")
        return "".join(streamed) if streamed else "\n".join(whole)
