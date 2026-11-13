"""Il giro completo sul websocket, con voce, orecchie e cervello finti."""

from fastapi.testclient import TestClient

from frankino.app import create_app


class FakeEars:
    name = "finto"

    async def transcribe(self, wav):
        return "che tempo fa?"


class FakeVoice:
    name = "finto"
    sample_rate = 24000

    async def speak(self, text):
        yield b"\x01\x00" * 10


class FakeAgent:
    def __init__(self, s, screen, gate):
        self.gate = gate

    async def start(self):
        pass

    async def stop(self):
        pass

    async def interrupt(self):
        pass

    async def ask(self, text, on_text):
        if "whatsapp" in text.lower():
            res = await self.gate.decide("mcp__claude_ai_WhatsApp__send_message", {"text": "ciao"})
            on_text("Mandato." if res else "Va bene, niente.")
            return "ok"
        on_text("Domani sole. ")
        on_text("Poche nuvole.")
        return "Domani sole. Poche nuvole."


def _messages(ws, until):
    out = []
    while True:
        m = ws.receive()
        if "text" in m and m["text"]:
            import json

            data = json.loads(m["text"])
            out.append(data)
            if data["type"] == until:
                return out
        else:
            out.append({"type": "bytes"})


def test_voce_in_entrata_voce_in_uscita(settings):
    app = create_app(settings, stt=FakeEars(), tts=FakeVoice(), agent_factory=FakeAgent)
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=prova") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json({"type": "start"})
            ws.send_bytes(b"\x00\x00" * 16000)
            ws.send_json({"type": "end"})
            got = _messages(ws, "done")
            kinds = [m["type"] for m in got]
            assert kinds[0] == "heard" and "say" in kinds and "bytes" in kinds
        rows = app.state.store.conn.execute("SELECT * FROM exchanges").fetchall()
        assert rows[0]["asked"] == "che tempo fa?"


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
