"""Il server: un websocket per i dispositivi, due rotte per i permessi, una per sapere se è vivo.

Va tenuto dietro Tailscale o la rete di casa. Ogni richiesta porta il gettone
`FRANKINO_TOKEN`: senza, il server rifiuta.
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket

from frankino import speech
from frankino.agent import Agent
from frankino.config import Settings
from frankino.session import AgentFactory, Session
from frankino.store import Store

log = logging.getLogger("frankino")

PURGE_EVERY_S = 6 * 3600


def _try(make, s: Settings, what: str):
    try:
        return make(s)
    except Exception as bad:  # noqa: BLE001 — il server parte lo stesso, senza quella parte
        log.warning("%s non disponibile: %s", what, bad)
        return None


def create_app(
    s: Settings | None = None,
    *,
    stt: speech.Transcriber | None = None,
    tts: speech.Speaker | None = None,
    agent_factory: AgentFactory = Agent,
) -> FastAPI:
    s = s or Settings.from_env()
    if not s.token:
        raise RuntimeError("Manca FRANKINO_TOKEN nel .env: senza gettone il server non parte.")
    store = Store(s.db_path, s.audio_dir)
    stt = stt or _try(speech.transcriber, s, "la trascrizione")
    tts = tts or _try(speech.speaker, s, "la voce")

    async def purge_forever() -> None:
        while True:
            removed = store.purge(s.audio_days)
            if removed:
                log.info("tolti %d audio più vecchi di %d giorni", removed, s.audio_days)
            await asyncio.sleep(PURGE_EVERY_S)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task = asyncio.create_task(purge_forever())
        yield
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    app = FastAPI(title="Frankino", lifespan=lifespan)

    def allowed(token: str) -> bool:
        return hmac.compare_digest(token.encode(), s.token.encode())

    @app.get("/salute")
    def health() -> dict:
        return {
            "ok": True,
            "model": s.model,
            "stt": stt.name if stt else None,
            "tts": tts.name if tts else None,
            "a2ui": s.a2ui_version,
        }

    @app.get("/permessi")
    def trust_list(token: str = Query("")) -> list[dict]:
        if not allowed(token):
            raise HTTPException(401)
        return store.trust_list()

    @app.post("/permessi/ritira")
    def trust_revoke(tool: str = Query(...), token: str = Query("")) -> dict:
        if not allowed(token):
            raise HTTPException(401)
        store.revoke(tool)
        return {"ok": True}

    @app.websocket("/ws")
    async def device(ws: WebSocket, token: str = "", device: str = "tablet") -> None:
        if not allowed(token):
            await ws.close(code=4401)
            return
        await ws.accept()
        await Session(ws, s, store, stt, tts, device, agent_factory).run()

    app.state.store = store
    return app
