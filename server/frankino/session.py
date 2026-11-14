"""Un dispositivo collegato: dal websocket alla voce e allo schermo, e ritorno.

Il protocollo sta in `docs/protocollo.md`. In breve: il tablet manda `start`,
poi pezzi binari di PCM (16 kHz, 16 bit, mono), poi `end`. Il server risponde
con `heard` (cosa ha capito), una serie di `say` seguiti dal loro audio binario
e chiusi da `say_end`, i messaggi `a2ui` per lo schermo, e `done` a fine turno.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from fastapi import WebSocket

from frankino import a2ui
from frankino.addressed import called, echo, silent
from frankino.agent import Agent
from frankino.audio import INPUT_RATE, louder, to_wav
from frankino.config import Settings
from frankino.confirm import ACTIONS, Gate, card, read_answer
from frankino.speech import Speaker, Transcriber
from frankino.store import Store
from frankino.text import Splitter

log = logging.getLogger("frankino.session")

MIN_SECONDS = 0.3
BROKEN = "Non arrivo al mio cervello. Riprova tra poco."
NOT_HEARD = "Non ti ho sentito bene, me lo ripeti?"
YES_OR_NO = "Dimmi sì, no, oppure non chiedermelo più."

# Perché il tablet ha cominciato ad ascoltare. Senza indicazione vale il caso più prudente.
WHY_NAME, WHY_FOLLOW = "name", "follow"
FOLLOW_PREFIX = "[seguito, senza nome] "

AgentFactory = Callable[[Settings, Any, Gate], Any]


class Session:
    def __init__(
        self,
        ws: WebSocket,
        s: Settings,
        store: Store,
        stt: Transcriber | None,
        tts: Speaker | None,
        device: str,
        agent_factory: AgentFactory = Agent,
    ) -> None:
        self.ws = ws
        self.s = s
        self.store = store
        self.stt = stt
        self.tts = tts
        self.device = device
        self.gate = Gate(store, self._ask_confirm, s.confirm_timeout_s)
        self.agent = agent_factory(s, a2ui.server(self._push_screen, s.a2ui_version), self.gate)
        self._lock = asyncio.Lock()
        self._speech: asyncio.Queue[str | asyncio.Event] = asyncio.Queue()
        self._cut = False
        self._pcm = bytearray()
        self._recording = False
        self._why = WHY_NAME
        self._said = ""
        self._turn: asyncio.Task | None = None
        self._tasks: set[asyncio.Task] = set()

    # ── il giro ────────────────────────────────────────────────────────────

    async def run(self) -> None:
        await self.agent.start()
        speaker = asyncio.create_task(self._speaker_loop())
        try:
            await self._send(
                {
                    "type": "ready",
                    "voice": bool(self.tts),
                    "ears": bool(self.stt),
                    "rate": self.tts.sample_rate if self.tts else None,
                    "a2ui": self.s.a2ui_version,
                }
            )
            while True:
                msg = await self.ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if msg.get("bytes") is not None:
                    if self._recording:
                        self._pcm.extend(msg["bytes"])
                elif msg.get("text"):
                    try:
                        data = json.loads(msg["text"])
                    except json.JSONDecodeError:
                        continue
                    await self._on_json(data)
        finally:
            for task in [speaker, self._turn, *self._tasks]:
                if task is not None:
                    task.cancel()
            with contextlib.suppress(Exception):
                await self.agent.stop()

    async def _on_json(self, m: dict[str, Any]) -> None:
        kind = m.get("type")
        if kind == "start":
            # Ha ricominciato a parlare: se Frankino stava parlando, tace.
            self._hush()
            self._pcm.clear()
            self._recording = True
            self._why = str(m.get("why") or WHY_NAME)
        elif kind == "end":
            self._recording = False
            pcm = bytes(self._pcm)
            self._pcm.clear()
            self._spawn(self._heard(pcm, int(m.get("rate") or INPUT_RATE), self._why))
        elif kind == "text":
            await self._handle(str(m.get("text", "")).strip(), None)
        elif kind == "action":
            await self._on_action(m)
        elif kind == "stop":
            self._hush()
            with contextlib.suppress(Exception):
                await self.agent.interrupt()

    async def _on_action(self, m: dict[str, Any]) -> None:
        name = str(m.get("name", ""))
        if name in ACTIONS:
            if self.gate.answer(ACTIONS[name]):
                await self._close_confirm()
            return
        # Un'altra azione sullo schermo: la si racconta a Claude come una frase.
        context = json.dumps(m.get("context", {}), ensure_ascii=False)
        await self._handle(f"[sullo schermo, superficie {m.get('surfaceId')}: azione «{name}» {context}]", None)

    async def _heard(self, pcm: bytes, rate: int, why: str = WHY_NAME) -> None:
        if len(pcm) / 2 / rate < MIN_SECONDS:
            return
        rid = self.store.save_recording(pcm, self.device, rate)
        if self.stt is None:
            self.store.set_transcript(rid, None, "-", "nessun servizio di trascrizione configurato")
            await self._send({"type": "error", "text": "Trascrizione non configurata sul server."})
            return
        try:
            text = await self.stt.transcribe(to_wav(louder(pcm), rate))
        except Exception as bad:  # noqa: BLE001 — si scrive e si dice
            log.exception("trascrizione fallita")
            self.store.set_transcript(rid, None, self.stt.name, repr(bad))
            self.say(NOT_HEARD)
            return
        # Il tablet si è svegliato da solo: se la frase non comincia col nome, nessuno lo chiamava.
        # Dopo una risposta, invece, conta solo che non sia l'eco della sua voce.
        if why == WHY_NAME and not called(text):
            await self._ignore(rid, "non chiamato")
            return
        if why == WHY_FOLLOW and (not text or echo(text, self._said)):
            await self._ignore(rid, "eco")
            return
        self.store.set_transcript(rid, text, self.stt.name)
        await self._send({"type": "heard", "text": text, "recording": rid})
        if text:
            await self._handle(text, rid, follow=why == WHY_FOLLOW)

    async def _ignore(self, rid: int | None, reason: str) -> None:
        """Non era per Frankino: non si risponde e non si tiene né l'audio né il testo."""
        if rid is not None:
            self.store.forget_recording(rid, reason)
        log.info("scartato: %s", reason)
        await self._send({"type": "ignored", "reason": reason})

    async def _handle(self, text: str, rid: int | None, follow: bool = False) -> None:
        if not text:
            return
        if self.gate.pending:
            answer = read_answer(text)
            if answer and self.gate.answer(answer):
                await self._close_confirm()
            else:
                self.say(YES_OR_NO)
            return
        if self._turn is not None and not self._turn.done():
            # Parla sopra a una risposta: si smette e si ascolta la nuova.
            self._hush()
            with contextlib.suppress(Exception):
                await self.agent.interrupt()
            with contextlib.suppress(BaseException):
                await asyncio.wait_for(self._turn, timeout=5)
        self._turn = asyncio.create_task(self._converse(text, rid, follow))

    async def _converse(self, text: str, rid: int | None, follow: bool = False) -> None:
        started = time.monotonic()
        await self._send({"type": "thinking"})
        splitter = Splitter()
        error = None
        answered = ""
        self._said = ""
        # Nel seguito senza nome Claude può rispondere solo «…» (parlavano fra loro): finché
        # arrivano solo puntini si aspetta, poi si parla o si tace.
        held: list[str] = []
        decided = not follow

        def piece(delta: str) -> None:
            nonlocal decided
            if not decided:
                held.append(delta)
                joined = "".join(held)
                if not joined.strip() or silent(joined):
                    return
                decided = True
                delta = joined
            for sentence in splitter.feed(delta):
                self.say(sentence)

        try:
            answered = await self.agent.ask(FOLLOW_PREFIX + text if follow else text, on_text=piece)
            if not decided:
                await self._ignore(rid, "non per me")
                return
            for sentence in splitter.flush():
                self.say(sentence)
        except asyncio.CancelledError:
            raise
        except Exception as bad:  # noqa: BLE001
            log.exception("il cervello non ha risposto")
            error = repr(bad)
            self.say(BROKEN)
        ms = int((time.monotonic() - started) * 1000)
        self.store.log_exchange(self.device, text, answered, ms, rid, error)
        # «done» arriva dopo l'ultima frase detta, non prima: il tablet sa che può tornare ad ascoltare.
        said = asyncio.Event()
        self._speech.put_nowait(said)
        await said.wait()
        await self._send({"type": "done", "ms": ms})

    # ── la voce ────────────────────────────────────────────────────────────

    def say(self, text: str) -> None:
        # Quello che ha detto nel turno, per riconoscere l'eco al giro dopo.
        self._said = (self._said + " " + text)[-2000:]
        self._speech.put_nowait(text)

    def _hush(self) -> None:
        self._cut = True
        while not self._speech.empty():
            item = self._speech.get_nowait()
            if isinstance(item, asyncio.Event):
                item.set()

    async def _speaker_loop(self) -> None:
        while True:
            text = await self._speech.get()
            if isinstance(text, asyncio.Event):
                text.set()
                continue
            self._cut = False
            await self._send(
                {
                    "type": "say",
                    "text": text,
                    "rate": self.tts.sample_rate if self.tts else None,
                }
            )
            if self.tts is not None:
                try:
                    async for chunk in self.tts.speak(text):
                        if self._cut:
                            break
                        await self._send_bytes(chunk)
                except Exception:  # noqa: BLE001
                    log.exception("la voce si è inceppata")
            await self._send({"type": "say_end"})

    # ── lo schermo e le conferme ───────────────────────────────────────────

    async def _push_screen(self, messages: list[dict]) -> None:
        await self._send({"type": "a2ui", "messages": messages})

    async def _ask_confirm(self, tool: str, args: dict[str, Any]) -> None:
        await self._push_screen(card(tool, args, self.s.a2ui_version))
        self.say("Lo faccio?")

    async def _close_confirm(self) -> None:
        await self._push_screen(a2ui.check([{"deleteSurface": {"surfaceId": "conferma"}}], self.s.a2ui_version))

    # ── il filo ────────────────────────────────────────────────────────────

    async def _send(self, data: dict[str, Any]) -> None:
        async with self._lock:
            with contextlib.suppress(Exception):
                await self.ws.send_text(json.dumps(data, ensure_ascii=False))

    async def _send_bytes(self, data: bytes) -> None:
        async with self._lock:
            with contextlib.suppress(Exception):
                await self.ws.send_bytes(data)

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
