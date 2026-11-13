"""Lo schermo. Claude descrive cosa mostrare in A2UI, il tablet lo disegna.

Lo strumento che Claude vede si chiama `mostra`: riceve una lista di messaggi
A2UI (createSurface, updateComponents, updateDataModel, deleteSurface), li
controlla quel tanto che basta per non mandare spazzatura al tablet, e li
inoltra. Se qualcosa non va, l'errore torna a Claude, che lo corregge da sé.

La versione del protocollo è `FRANKINO_A2UI_VERSION`: di partenza `v0.9.1`,
che è quella che legge il renderer Android ufficiale.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

MESSAGE_KEYS = ("createSurface", "updateComponents", "updateDataModel", "deleteSurface")

CATALOGS = {
    "v0.9.1": "https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json",
    "1.0": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json",
}

Push = Callable[[list[dict]], Awaitable[None]]


class Invalid(ValueError):
    pass


def check(messages: Any, version: str) -> list[dict]:
    """I messaggi pronti da mandare, con la versione messa se mancava. Solleva `Invalid`."""
    if isinstance(messages, str):
        try:
            messages = json.loads(messages)
        except json.JSONDecodeError as bad:
            raise Invalid(f"non è JSON valido: {bad}") from bad
    if isinstance(messages, dict):
        messages = [messages]
    if not isinstance(messages, list) or not messages:
        raise Invalid("serve una lista non vuota di messaggi A2UI")

    out: list[dict] = []
    for i, msg in enumerate(messages):
        where = f"messaggio {i + 1}"
        if not isinstance(msg, dict):
            raise Invalid(f"{where}: dev'essere un oggetto")
        keys = [k for k in MESSAGE_KEYS if k in msg]
        if len(keys) != 1:
            raise Invalid(f"{where}: serve esattamente una chiave fra {', '.join(MESSAGE_KEYS)}")
        body = msg[keys[0]]
        if not isinstance(body, dict) or not body.get("surfaceId"):
            raise Invalid(f"{where}: manca surfaceId")
        if keys[0] == "createSurface" and not body.get("catalogId"):
            body["catalogId"] = CATALOGS.get(version, CATALOGS["v0.9.1"])
        if keys[0] == "updateComponents":
            comps = body.get("components")
            if not isinstance(comps, list) or not comps:
                raise Invalid(f"{where}: components dev'essere una lista non vuota")
            for c in comps:
                if not isinstance(c, dict) or not c.get("id") or not c.get("component"):
                    raise Invalid(f"{where}: ogni componente vuole id e component")
        out.append({"version": version, keys[0]: body})
    return out


def server(push: Push, version: str):
    """Il piccolo server MCP, dentro il processo, con l'unico strumento `mostra`."""
    from claude_agent_sdk import create_sdk_mcp_server, tool

    @tool(
        "mostra",
        "Mostra qualcosa sullo schermo del tablet con messaggi A2UI. Usalo per tutto quello "
        "che si capisce meglio guardando: ricette, liste, elenchi, confronti, orari, "
        "conferme. Passa la lista completa di messaggi (createSurface, updateComponents, "
        "updateDataModel, deleteSurface).",
        {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Messaggi A2UI, nell'ordine.",
                }
            },
            "required": ["messages"],
        },
    )
    async def mostra(args: dict[str, Any]) -> dict[str, Any]:
        try:
            ready = check(args.get("messages"), version)
        except Invalid as bad:
            return {"content": [{"type": "text", "text": f"Non mostrato: {bad}"}], "is_error": True}
        await push(ready)
        return {"content": [{"type": "text", "text": "Mostrato sullo schermo."}]}

    return create_sdk_mcp_server(name="schermo", version="1.0.0", tools=[mostra])
