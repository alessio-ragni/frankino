"""Quello che resta scritto: registrazioni, scambi, permessi «non chiedermelo più».

Un file SQLite sul server, niente di più. Gli audio stanno su disco accanto, uno
per registrazione, e dopo `FRANKINO_AUDIO_DAYS` giorni si cancellano: il testo
trascritto resta, e la riga dice quando l'audio è stato tolto.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from frankino.audio import INPUT_RATE, seconds, to_wav

SCHEMA = """
CREATE TABLE IF NOT EXISTS recordings (
  id          INTEGER PRIMARY KEY,
  at          TEXT NOT NULL,              -- UTC, ISO
  device      TEXT NOT NULL,
  seconds     REAL NOT NULL,
  path        TEXT,                       -- NULL dopo la pulizia
  transcript  TEXT,
  engine      TEXT,
  error       TEXT,
  purged_at   TEXT
);
CREATE TABLE IF NOT EXISTS exchanges (
  id            INTEGER PRIMARY KEY,
  at            TEXT NOT NULL,
  device        TEXT NOT NULL,
  recording_id  INTEGER REFERENCES recordings(id),
  asked         TEXT NOT NULL,
  answered      TEXT NOT NULL,
  ms            INTEGER,
  error         TEXT
);
CREATE TABLE IF NOT EXISTS trust (
  tool        TEXT PRIMARY KEY,           -- nome completo dello strumento, es. mcp__claude_ai_WhatsApp__send_message
  granted_at  TEXT NOT NULL,
  revoked_at  TEXT                        -- un permesso ritirato resta scritto
);
"""


def _now() -> datetime:
    return datetime.now(UTC)


class Store:
    def __init__(self, db_path: Path, audio_dir: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir = audio_dir
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    # ── registrazioni ──────────────────────────────────────────────────────

    def save_recording(self, pcm: bytes, device: str, rate: int = INPUT_RATE) -> int:
        at = _now()
        cur = self.conn.execute(
            "INSERT INTO recordings (at, device, seconds) VALUES (?, ?, ?)",
            (at.isoformat(), device, seconds(pcm, rate)),
        )
        rid = int(cur.lastrowid)
        folder = self.audio_dir / at.strftime("%Y-%m-%d")
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{rid}.wav"
        path.write_bytes(to_wav(pcm, rate))
        self.conn.execute("UPDATE recordings SET path = ? WHERE id = ?", (str(path), rid))
        self.conn.commit()
        return rid

    def set_transcript(self, rid: int, text: str | None, engine: str, error: str | None = None) -> None:
        self.conn.execute(
            "UPDATE recordings SET transcript = ?, engine = ?, error = ? WHERE id = ?",
            (text, engine, error, rid),
        )
        self.conn.commit()

    def purge(self, days: int, now: datetime | None = None) -> int:
        """Toglie gli audio più vecchi di `days` giorni. Il testo resta."""
        limit = ((now or _now()) - timedelta(days=days)).isoformat()
        rows = self.conn.execute(
            "SELECT id, path FROM recordings WHERE path IS NOT NULL AND at < ?", (limit,)
        ).fetchall()
        stamp = (now or _now()).isoformat()
        for row in rows:
            Path(row["path"]).unlink(missing_ok=True)
            self.conn.execute("UPDATE recordings SET path = NULL, purged_at = ? WHERE id = ?", (stamp, row["id"]))
        self.conn.commit()
        return len(rows)

    # ── scambi ─────────────────────────────────────────────────────────────

    def log_exchange(
        self,
        device: str,
        asked: str,
        answered: str,
        ms: int,
        recording_id: int | None = None,
        error: str | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO exchanges (at, device, recording_id, asked, answered, ms, error) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_now().isoformat(), device, recording_id, asked, answered, ms, error),
        )
        self.conn.commit()

    # ── permessi ───────────────────────────────────────────────────────────

    def trusted(self, tool: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM trust WHERE tool = ? AND revoked_at IS NULL", (tool,)).fetchone()
        return row is not None

    def grant(self, tool: str) -> None:
        self.conn.execute(
            "INSERT INTO trust (tool, granted_at) VALUES (?, ?)"
            " ON CONFLICT(tool) DO UPDATE SET granted_at = excluded.granted_at, revoked_at = NULL",
            (tool, _now().isoformat()),
        )
        self.conn.commit()

    def revoke(self, tool: str) -> None:
        self.conn.execute(
            "UPDATE trust SET revoked_at = ? WHERE tool = ? AND revoked_at IS NULL",
            (_now().isoformat(), tool),
        )
        self.conn.commit()

    def trust_list(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM trust ORDER BY granted_at DESC").fetchall()
        return [dict(r) for r in rows]
