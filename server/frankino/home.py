"""Frankino's own tools: alarms, timers, reminders, lists, and "I have no tool for that".

They are Claude tools like the connectors, in an in-process MCP server called
`home`. They only touch Frankino's own database and the tablet, so they do not
go through the confirmation gate.

* **Alarms** go to the tablet's Clock app (so they ring even if Frankino is
  down) and are written in the agenda, so Frankino can list them.
* **Timers and reminders** ring from Frankino: a tone and his voice, never over
  a conversation (`bell.py`).
* Nothing is deleted: an item ends with `ended_at` and the reason.

Time is local, from `FRANKINO_TZ`, and written to the second: a 7:00 alarm
stays at 7:00 across daylight saving.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from frankino.store import Store

FMT = "%Y-%m-%d %H:%M:%S"
SHOPPING = "spesa"
DAYS = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}


def local_now(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz)).replace(tzinfo=None, microsecond=0)


def parse_when(text: str, now: datetime) -> datetime:
    """'2026-11-16 07:00' or '07:00' (today, or tomorrow if already past)."""
    raw = str(text).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    for fmt in ("%H:%M", "%H.%M"):
        try:
            t = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        when = now.replace(hour=t.hour, minute=t.minute, second=0)
        return when if when > now else when + timedelta(days=1)
    raise ValueError(f"time {text!r}: use 'YYYY-MM-DD HH:MM' or 'HH:MM'")


def spoken_when(when: datetime, now: datetime) -> str:
    days = (when.date() - now.date()).days
    hour = f"{when:%H:%M}"
    if days == 0:
        return f"oggi alle {hour}"
    if days == 1:
        return f"domani alle {hour}"
    return f"{when:%d/%m} alle {hour}"


class Host(Protocol):
    """What the session offers these tools."""

    async def device(self, action: dict[str, Any]) -> bool: ...

    async def agenda_changed(self) -> None: ...

    async def list_changed(self, name: str) -> None: ...

    def missing(self, what: str, why: str) -> None: ...


def _ok(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def _err(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "is_error": True}


def agenda_rows(store: Store, now: datetime) -> list[dict]:
    out = []
    for item in store.agenda_live():
        due = datetime.strptime(item["due_at"], FMT)
        if item["kind"] == "alarm" and due < now and not item["repeat_days"]:
            continue
        out.append({**item, "spoken": spoken_when(due, now)})
    return out


def server(store: Store, host: Host, tz: str):
    from claude_agent_sdk import create_sdk_mcp_server

    return create_sdk_mcp_server(name="home", version="2.0.0", tools=tools(store, host, tz))


def tools(store: Store, host: Host, tz: str) -> list:
    """The tool objects (each has `.name` and `.handler`), apart so tests can call them."""
    from claude_agent_sdk import tool

    @tool(
        "set_alarm",
        "Set a wake-up alarm on the tablet's Clock app (it rings even if Frankino is off). "
        "time: 'YYYY-MM-DD HH:MM' or 'HH:MM'. repeat: optional weekdays like ['mon','tue'].",
        {
            "type": "object",
            "properties": {
                "time": {"type": "string"},
                "label": {"type": "string"},
                "repeat": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["time"],
        },
    )
    async def set_alarm(args: dict[str, Any]) -> dict[str, Any]:
        now = local_now(tz)
        try:
            when = parse_when(args.get("time", ""), now)
        except ValueError as bad:
            return _err(str(bad))
        days = [DAYS[d[:3].lower()] for d in args.get("repeat") or [] if d[:3].lower() in DAYS]
        label = str(args.get("label") or "Sveglia")
        ok = await host.device(
            {"action": "set_alarm", "hour": when.hour, "minute": when.minute, "days": days, "label": label}
        )
        if not ok:
            return _err("The tablet could not set the alarm (app not in front, or no Clock app). Say so.")
        store.agenda_add("alarm", when.strftime(FMT), label, ",".join(map(str, days)) or None)
        await host.agenda_changed()
        return _ok(f"Alarm set in the Clock app for {spoken_when(when, now)}.")

    @tool(
        "set_timer",
        "Start a timer that Frankino rings with his voice. minutes may be decimal (0.5 = 30 seconds).",
        {
            "type": "object",
            "properties": {"minutes": {"type": "number"}, "label": {"type": "string"}},
            "required": ["minutes"],
        },
    )
    async def set_timer(args: dict[str, Any]) -> dict[str, Any]:
        try:
            minutes = float(args.get("minutes"))
        except (TypeError, ValueError):
            return _err("minutes must be a number")
        if not 0 < minutes <= 24 * 60:
            return _err("minutes must be between 0 and 1440")
        now = local_now(tz)
        when = now + timedelta(seconds=round(minutes * 60))
        store.agenda_add("timer", when.strftime(FMT), str(args.get("label") or ""))
        await host.agenda_changed()
        return _ok(f"Timer running, it rings at {when:%H:%M:%S}.")

    @tool(
        "set_reminder",
        "Remind the person of something at a given time: Frankino says it aloud then. "
        "time: 'YYYY-MM-DD HH:MM' or 'HH:MM'.",
        {
            "type": "object",
            "properties": {"time": {"type": "string"}, "text": {"type": "string"}},
            "required": ["time", "text"],
        },
    )
    async def set_reminder(args: dict[str, Any]) -> dict[str, Any]:
        now = local_now(tz)
        try:
            when = parse_when(args.get("time", ""), now)
        except ValueError as bad:
            return _err(str(bad))
        store.agenda_add("reminder", when.strftime(FMT), str(args.get("text") or ""))
        await host.agenda_changed()
        return _ok(f"Reminder set for {spoken_when(when, now)}.")

    @tool(
        "agenda",
        "List the live alarms, timers and reminders (also shows them on the agenda card).",
        {"type": "object", "properties": {}},
    )
    async def agenda(args: dict[str, Any]) -> dict[str, Any]:
        rows = agenda_rows(store, local_now(tz))
        await host.agenda_changed()
        if not rows:
            return _ok("Nothing in the agenda.")
        return _ok("\n".join(f"#{r['id']} {r['kind']} {r['spoken']} {r['label']}".strip() for r in rows))

    @tool(
        "cancel",
        "Cancel an alarm, timer or reminder by its #id (from agenda).",
        {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
    )
    async def cancel(args: dict[str, Any]) -> dict[str, Any]:
        item = store.agenda_get(int(args.get("id") or 0))
        if item is None or item["ended_at"]:
            return _err("No live item with that id. Call agenda first.")
        store.agenda_end(item["id"], "cancelled")
        note = ""
        if item["kind"] == "alarm":
            due = datetime.strptime(item["due_at"], FMT)
            ok = await host.device(
                {"action": "dismiss_alarm", "hour": due.hour, "minute": due.minute, "label": item["label"]}
            )
            if not ok:
                note = " The Clock app may still have it: tell the person to check."
        await host.agenda_changed()
        return _ok("Cancelled." + note)

    @tool(
        "list_add",
        f"Add things to a household list (default '{SHOPPING}', the shopping list). Shows the list card.",
        {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "string"}}, "list": {"type": "string"}},
            "required": ["items"],
        },
    )
    async def list_add(args: dict[str, Any]) -> dict[str, Any]:
        name = str(args.get("list") or SHOPPING).lower()
        added = [i for i in args.get("items") or [] if i.strip() and store.list_add(name, i.strip())]
        await host.list_changed(name)
        return _ok(f"Added: {', '.join(added) or 'nothing new'}.")

    @tool(
        "list_remove",
        "Remove things from a household list. done=true just ticks them off instead (bought).",
        {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": {"type": "string"}},
                "list": {"type": "string"},
                "done": {"type": "boolean"},
            },
            "required": ["items"],
        },
    )
    async def list_remove(args: dict[str, Any]) -> dict[str, Any]:
        name = str(args.get("list") or SHOPPING).lower()
        hit, miss = [], []
        for i in args.get("items") or []:
            got = store.list_check(name, i) if args.get("done") else store.list_remove(name, i)
            (hit if got else miss).append(got or i)
        await host.list_changed(name)
        text = f"Done: {', '.join(hit) or 'nothing'}."
        return _ok(text + (f" Not on the list: {', '.join(miss)}." if miss else ""))

    @tool(
        "list_show",
        "Show a household list on its card and read what is on it. clear=true empties it (only_done=true "
        "removes only the ticked ones).",
        {
            "type": "object",
            "properties": {"list": {"type": "string"}, "clear": {"type": "boolean"}, "only_done": {"type": "boolean"}},
        },
    )
    async def list_show(args: dict[str, Any]) -> dict[str, Any]:
        name = str(args.get("list") or SHOPPING).lower()
        if args.get("clear"):
            store.list_clear(name, bool(args.get("only_done")))
        await host.list_changed(name)
        rows = store.list_items(name)
        if not rows:
            return _ok(f"The list '{name}' is empty.")
        return _ok(", ".join(r["item"] + (" (preso)" if r["done"] else "") for r in rows))

    @tool(
        "report_missing",
        "Call this whenever you cannot do what was asked because you lack a tool or a connector "
        "(e.g. turning on lights, playing music). It is logged so the owner can add it.",
        {
            "type": "object",
            "properties": {"what": {"type": "string"}, "why": {"type": "string"}},
            "required": ["what"],
        },
    )
    async def report_missing(args: dict[str, Any]) -> dict[str, Any]:
        host.missing(str(args.get("what", "")), str(args.get("why", "")))
        return _ok("Logged. Tell the person briefly you cannot do it yet.")

    return [set_alarm, set_timer, set_reminder, agenda, cancel, list_add, list_remove, list_show, report_missing]
