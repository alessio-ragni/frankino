"""Le azioni verso fuori chiedono il permesso, finché non gli dici di smettere.

Ogni volta che Claude vuole usare uno strumento passa di qui. Se lo strumento
manda qualcosa fuori (un WhatsApp, una mail, un evento) e quel tipo non è già
stato autorizzato, la chiamata si ferma: lo schermo mostra cosa sta per fare,
la voce chiede «lo faccio?», e si aspetta un «sì», un «no», o un «non
chiedermelo più» (a voce o col pulsante). Il «non chiedermelo più» vale per
quello strumento, resta scritto, e si ritira.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from frankino.store import Store

Answer = Literal["yes", "always", "no"]

# Prudenti per costruzione: ogni strumento esterno chiede il permesso, TRANNE quelli
# il cui nome dice chiaramente che leggono soltanto. Il contrario (elencare i verbi
# che mandano fuori) si era già rotto due volte nella prima prova: i connettori
# hanno nomi in inglese e in italiano («calendario_crea»), e un verbo mancante
# vuol dire un'azione partita senza chiedere.
_READ_ONLY = {
    "search",
    "list",
    "get",
    "read",
    "find",
    "fetch",
    "download",
    "transcribe",
    "suggest",
    "query",
    "guide",
    "whoami",
    "status",
    "describe",
    "explore",
    "show",
    "analyze",
    "balance",
    "cerca",
    "leggi",
    "elenca",
    "oggi",
    "dammi",
    "istruzioni",
    "chi",
}
# Una bozza non parte da sola.
_DRAFT = {"draft", "drafts", "bozza", "bozze"}

_ALWAYS = re.compile(r"\bnon\s+(me\s+lo\s+|mi\s+)?chieder(lo|melo|mi)\s+più\b|\bsempre\b", re.I)
_NO = re.compile(r"^\s*(no|non\b|annulla|lascia\s+stare|aspetta|fermo|ferma|stop)", re.I)
_YES = re.compile(r"^\s*(sì|si|ok|okay|vai|manda|mandalo|mandala|certo|procedi|conferma|fallo)", re.I)

OWN_SERVER = "mcp__schermo__"


def is_outward(tool: str) -> bool:
    if not tool.startswith("mcp__") or tool.startswith(OWN_SERVER):
        return False
    words = set(re.split(r"[_\W]+", tool.rsplit("__", 1)[-1].lower()))
    if "send" in words or "invia" in words or "manda" in words:
        return True
    return not (words & _READ_ONLY or words & _DRAFT)


def read_answer(text: str) -> Answer | None:
    if _ALWAYS.search(text):
        return "always"
    if _NO.search(text):
        return "no"
    if _YES.search(text):
        return "yes"
    return None


def label(tool: str) -> str:
    """«mcp__claude_ai_WhatsApp__send_message» → «WhatsApp · send message»."""
    parts = tool.split("__")
    service = parts[1].removeprefix("claude_ai_").replace("_", " ") if len(parts) > 2 else tool
    return f"{service} · {parts[-1].replace('_', ' ')}"


Ask = Callable[[str, dict[str, Any]], Awaitable[None]]


class Gate:
    """Il cancello davanti a ogni strumento, con l'attesa della risposta."""

    def __init__(self, store: Store, ask: Ask, timeout_s: float = 120) -> None:
        self.store = store
        self.ask = ask
        self.timeout_s = timeout_s
        self._waiting: asyncio.Future[Answer] | None = None
        self.pending_tool: str | None = None

    @property
    def pending(self) -> bool:
        return self._waiting is not None and not self._waiting.done()

    def answer(self, answer: Answer) -> bool:
        if not self.pending:
            return False
        assert self._waiting is not None
        self._waiting.set_result(answer)
        return True

    async def decide(self, tool: str, args: dict[str, Any]) -> bool:
        """True se lo strumento può andare. Le azioni verso fuori aspettano la risposta."""
        if not is_outward(tool) or self.store.trusted(tool):
            return True

        self._waiting = asyncio.get_running_loop().create_future()
        self.pending_tool = tool
        try:
            await self.ask(tool, args)
            got = await asyncio.wait_for(self._waiting, timeout=self.timeout_s)
        except TimeoutError:
            got = "no"
        finally:
            self._waiting = None
            self.pending_tool = None

        if got == "always":
            self.store.grant(tool)
        return got in ("yes", "always")

    async def pre_tool_use(self, data: dict[str, Any], tool_use_id: str | None, context: Any):
        """L'hook PreToolUse dell'Agent SDK.

        È un hook e non il `can_use_tool`, apposta: il `can_use_tool` viene
        chiamato solo quando Claude Code chiederebbe il permesso, e con le
        impostazioni di chi lo ospita (modalità «auto», regole «allow») non lo
        chiede quasi mai. L'hook passa da qui per ogni strumento, sempre.
        """
        ok = await self.decide(str(data.get("tool_name", "")), dict(data.get("tool_input") or {}))
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow" if ok else "deny",
                "permissionDecisionReason": ("" if ok else "L'utente ha detto di no, o non ha risposto. Non farlo."),
            }
        }


def card(tool: str, args: dict[str, Any], version: str) -> list[dict]:
    """La scheda di conferma, costruita qui e non da Claude: deve essere sempre uguale e onesta."""
    lines = []
    for key, value in args.items():
        shown = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        lines.append(f"**{key}**: {shown[:400]}")
    from frankino.a2ui import check

    sid = "conferma"
    comps = [
        {"id": "root", "component": "Card", "child": "col"},
        {"id": "col", "component": "Column", "children": ["title", "body", "buttons"]},
        {"id": "title", "component": "Text", "text": f"Lo faccio? — {label(tool)}", "variant": "h3"},
        {"id": "body", "component": "Text", "text": "\n\n".join(lines) or "(nessun dettaglio)"},
        {"id": "buttons", "component": "Row", "children": ["yes", "always", "no"]},
        {"id": "yes_t", "component": "Text", "text": "Sì"},
        {"id": "always_t", "component": "Text", "text": "Non chiedermelo più"},
        {"id": "no_t", "component": "Text", "text": "No"},
        {
            "id": "yes",
            "component": "Button",
            "child": "yes_t",
            "variant": "primary",
            "action": {"event": {"name": "confirm_yes"}},
        },
        {"id": "always", "component": "Button", "child": "always_t", "action": {"event": {"name": "confirm_always"}}},
        {
            "id": "no",
            "component": "Button",
            "child": "no_t",
            "variant": "borderless",
            "action": {"event": {"name": "confirm_no"}},
        },
    ]
    return check(
        [{"createSurface": {"surfaceId": sid}}, {"updateComponents": {"surfaceId": sid, "components": comps}}],
        version,
    )


ACTIONS: dict[str, Answer] = {"confirm_yes": "yes", "confirm_always": "always", "confirm_no": "no"}
