"""Il giro completo sul websocket, con voce, orecchie e cervello finti."""

from fastapi.testclient import TestClient

from frankino.app import create_app


class FakeEars:
    name = "finto"

    def __init__(self, text="Franco, che tempo fa?"):
        self.text = text

    async def transcribe(self, wav):
        return self.text


class FakeVoice:
    name = "finto"
    sample_rate = 24000

    async def speak(self, text):
        yield b"\x01\x00" * 10


class FakeAgent:
    asked: list[str] = []

    def __init__(self, s, screen, gate):
        self.gate = gate

    async def start(self):
        pass

    async def stop(self):
        pass

    async def interrupt(self):
        pass

    async def ask(self, text, on_text):
        FakeAgent.asked.append(text)
        if "chiacchiere" in text:
            on_text("…")
            return "…"
        if "whatsapp" in text.lower():
            res = await self.gate.decide("mcp__claude_ai_WhatsApp__send_message", {"text": "ciao"})
            on_text("Mandato." if res else "Va bene, niente.")
            return "ok"
        on_text("Domani sole. ")
        on_text("Poche nuvole.")
        return "Domani sole. Poche nuvole."


def _messages(ws, *until):
    out = []
    while True:
        m = ws.receive()
        if "text" in m and m["text"]:
            import json

            data = json.loads(m["text"])
            out.append(data)
            if data["type"] in until:
                return out
        else:
            out.append({"type": "bytes"})


def _speak(ws, why=None):
    start = {"type": "start"}
    if why:
        start["why"] = why
    ws.send_json(start)
    ws.send_bytes(b"\x00\x00" * 16000)
    ws.send_json({"type": "end"})
    return _messages(ws, "done", "ignored")


def test_voce_in_entrata_voce_in_uscita(settings):
    app = create_app(settings, stt=FakeEars(), tts=FakeVoice(), agent_factory=FakeAgent)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=prova") as ws:
            assert ws.receive_json()["type"] == "ready"
            got = _speak(ws, "name")
            kinds = [m["type"] for m in got]
            assert kinds[0] == "heard" and "say" in kinds and "bytes" in kinds
        rows = app.state.store.conn.execute("SELECT * FROM exchanges").fetchall()
        assert rows[0]["asked"] == "Franco, che tempo fa?"


def test_senza_nome_si_butta_tutto(settings):
    app = create_app(settings, stt=FakeEars("la partita dura un'ora e mezza"), tts=FakeVoice(), agent_factory=FakeAgent)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=prova") as ws:
            ws.receive_json()
            got = _speak(ws)  # senza «why» vale il caso prudente: svegliato dal nome
            assert got[-1] == {"type": "ignored", "reason": "non chiamato"}
            assert all(m["type"] != "heard" for m in got)
        store = app.state.store
        row = store.conn.execute("SELECT * FROM recordings").fetchone()
        assert row["transcript"] is None and row["path"] is None and row["error"] == "non chiamato"
        assert not list(settings.audio_dir.rglob("*.wav"))
        assert store.conn.execute("SELECT COUNT(*) FROM exchanges").fetchone()[0] == 0


def test_col_pulsante_il_nome_non_serve(settings):
    app = create_app(settings, stt=FakeEars("che tempo fa?"), tts=FakeVoice(), agent_factory=FakeAgent)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=prova") as ws:
            ws.receive_json()
            assert _speak(ws, "button")[-1]["type"] == "done"


def test_nel_seguito_la_sua_eco_si_butta(settings):
    ears = FakeEars("Franco, che tempo fa?")
    app = create_app(settings, stt=ears, tts=FakeVoice(), agent_factory=FakeAgent)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=prova") as ws:
            ws.receive_json()
            _speak(ws, "name")
            ears.text = "Domani sole, poche nuvole."
            assert _speak(ws, "follow")[-1] == {"type": "ignored", "reason": "eco"}


def test_nel_seguito_se_non_parlano_a_lui_tace(settings):
    FakeAgent.asked = []
    app = create_app(settings, stt=FakeEars("chiacchiere fra noi"), tts=FakeVoice(), agent_factory=FakeAgent)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=prova") as ws:
            ws.receive_json()
            got = _speak(ws, "follow")
            assert got[-1] == {"type": "ignored", "reason": "non per me"}
            assert all(m["type"] != "say" for m in got)
        assert FakeAgent.asked[-1].startswith("[seguito, senza nome] ")
        row = app.state.store.conn.execute("SELECT * FROM recordings").fetchone()
        assert row["transcript"] is None


def test_nel_seguito_una_domanda_vera_ha_risposta(settings):
    app = create_app(settings, stt=FakeEars("e dopodomani?"), tts=FakeVoice(), agent_factory=FakeAgent)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=prova") as ws:
            ws.receive_json()
            got = _speak(ws, "follow")
            assert got[-1]["type"] == "done" and any(m["type"] == "say" for m in got)


def test_la_conferma_passa_dalla_voce(settings):
    app = create_app(settings, stt=FakeEars(), tts=FakeVoice(), agent_factory=FakeAgent)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=prova") as ws:
            ws.receive_json()
            ws.send_json({"type": "text", "text": "manda un whatsapp"})
            got = _messages(ws, "a2ui")
            assert got[-1]["messages"][0]["createSurface"]["surfaceId"] == "conferma"
            ws.send_json({"type": "text", "text": "sì"})
            got = _messages(ws, "done")
            assert any(m.get("text") == "Mandato." for m in got)


def test_senza_gettone_niente(settings):
    app = create_app(settings, stt=FakeEars(), tts=FakeVoice(), agent_factory=FakeAgent)
    with TestClient(app) as client:
        import pytest
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws?token=sbagliato") as ws:
                ws.receive_json()
