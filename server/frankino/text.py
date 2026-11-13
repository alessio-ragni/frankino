"""Dal testo che arriva a pezzi alle frasi da dire.

Claude scrive la risposta un pezzo alla volta. Per cominciare a parlare il prima
possibile si dice tutto quello che sta prima dell'ultima fine di frase, e il
resto aspetta il pezzo dopo. A frase e non a parola: una frase è il pezzo più
corto che ha ancora una sua intonazione.

Ripreso dal Franco di casa, dove ha già fatto la sua strada.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator

MAX_CHARS = 240

END = re.compile(r"(?<=[.!?…;:])\s+|\n+")
_PAUSE = re.compile(r"(?<=[,;:—–])\s+")
_SPACES = re.compile(r"[^\S\n]+")
_AROUND_NEWLINE = re.compile(r"\s*\n\s*")
_LOOSE_PUNCT = re.compile(r"[^\S\n]+(?=[,.;:!?…)\]])")
# Markdown che una voce leggerebbe ad alta voce: asterischi, cancelletti, trattini d'elenco.
_MARKDOWN = re.compile(r"(\*\*|__|`+|^#+\s*|^\s*[-*•]\s+)", re.MULTILINE)
_DROP = {"Cc", "Cf", "Cs", "Co", "Cn", "So", "Sk"}


def clean(text: str) -> str:
    text = _MARKDOWN.sub("", text)
    kept = []
    for char in unicodedata.normalize("NFKC", text):
        if char == "\n":
            kept.append(char)
        elif unicodedata.category(char) in _DROP:
            kept.append(" ")
        else:
            kept.append(char)
    collapsed = _LOOSE_PUNCT.sub("", _SPACES.sub(" ", "".join(kept)))
    return _AROUND_NEWLINE.sub("\n", collapsed).strip()


def sentences(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    pieces: list[str] = []
    for chunk in END.split(clean(text)):
        stripped = chunk.strip()
        if stripped:
            pieces.extend(shorten(stripped, max_chars))
    return pieces


def shorten(piece: str, limit: int) -> list[str]:
    if len(piece) <= limit:
        return [piece]
    out: list[str] = []
    current = ""
    for bit in _fragments(piece, limit):
        if not current:
            current = bit
        elif len(current) + 1 + len(bit) <= limit:
            current = f"{current} {bit}"
        else:
            out.append(current)
            current = bit
    if current:
        out.append(current)
    return out


def _fragments(piece: str, limit: int) -> Iterator[str]:
    for part in _PAUSE.split(piece):
        while len(part) > limit:
            cut = part.rfind(" ", 0, limit)
            head, part = (part[:cut], part[cut:]) if cut > 0 else (part[:limit], part[limit:])
            if head.strip():
                yield head.strip()
            part = part.strip()
        if part:
            yield part


class Splitter:
    """Prende i pezzi come arrivano e restituisce le frasi già dicibili."""

    def __init__(self, max_chars: int = MAX_CHARS) -> None:
        self.max_chars = max_chars
        self._buffer = ""

    def feed(self, delta: str) -> list[str]:
        if not delta:
            return []
        self._buffer += delta
        out: list[str] = []
        last = None
        for match in END.finditer(self._buffer):
            last = match
        if last is not None:
            ready, self._buffer = self._buffer[: last.end()], self._buffer[last.end() :]
            out.extend(sentences(ready, self.max_chars))
        while len(self._buffer) > self.max_chars:
            head, self._buffer = self._buffer[: self.max_chars], self._buffer[self.max_chars :]
            out.extend(sentences(head, self.max_chars))
        return out

    def flush(self) -> list[str]:
        rest, self._buffer = self._buffer, ""
        return sentences(rest, self.max_chars)
