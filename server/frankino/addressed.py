"""Parlavano davvero a Frankino? Il secondo controllo, sulla trascrizione vera.

Il tablet si sveglia con un riconoscitore piccolo, che ogni tanto «sente» il nome in mezzo
a un discorso qualunque. Qui si guarda il testo trascritto: se non comincia col nome
(dopo al più due saluti), nessuno lo stava chiamando e la registrazione si butta.

Dopo una risposta il tablet ascolta qualche secondo senza nome: lì l'unico controllo
possibile è che non sia l'eco della sua stessa voce.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

NAMES = ("franco", "franko", "franchino", "frankino")

# Saluti e intercalari che si dicono prima del nome: «ehi Franco», «senti Franco», «no, Franco».
GREETINGS = frozenset(
    {
        "ehi",
        "hey",
        "hei",
        "ei",
        "ehy",
        "e",
        "eh",
        "oh",
        "ciao",
        "hi",
        "hello",
        "ok",
        "okay",
        "no",
        "dai",
        "senti",
        "scusa",
        "allora",
        "ascolta",
    }
)

# Parole vere che somigliano al nome: non sono un richiamo.
NOT_NAMES = frozenset(
    {
        "franca",
        "franche",
        "franchi",
        "franchini",
        "francia",
        "francese",
        "francesi",
        "francesca",
        "francesco",
        "franceschi",
        "frana",
        "frane",
        "franato",
        "france",
        "frances",
        "franchise",
        "branco",
        "fianco",
        "fresco",
        "freno",
        "frego",
        "frano",
        "fronte",
    }
)

MAX_GREETINGS = 2


def words(text: str) -> list[str]:
    """Parole in minuscolo, senza accenti né punteggiatura."""
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return re.findall(r"[a-z]+", plain)


def _distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def is_name(word: str) -> bool:
    if word in NOT_NAMES or len(word) < 4:
        return False
    if word in NAMES:
        return True
    # «Fraco», «Frank», «Franchina»: storpiature del trascrittore. Due lettere di scarto solo se
    # comincia come il nome, altrimenti «fanno» o «banco» passerebbero.
    limit = 2 if word.startswith("fr") else 1
    return any(_distance(word, name) <= limit for name in NAMES)


def called(text: str) -> bool:
    """Vero se la frase comincia col nome, al più dopo due saluti («ehi Franco», «ciao Franchino»)."""
    ws = words(text)
    i = 0
    while i < len(ws) and i < MAX_GREETINGS and ws[i] in GREETINGS and not is_name(ws[i]):
        i += 1
    return i < len(ws) and is_name(ws[i])


def echo(text: str, said: str) -> bool:
    """Vero se `text` è quasi la stessa cosa che Frankino ha appena detto (il microfono ha sentito lui)."""
    heard = " ".join(words(text))
    spoken = " ".join(words(said))
    if not heard or not spoken:
        return False
    if len(heard) >= 8 and heard in spoken:
        return True
    return SequenceMatcher(None, heard, spoken).ratio() >= 0.8


SILENT = "…"


def silent(answer: str) -> bool:
    """La risposta convenuta per «non parlavano a me»: solo puntini."""
    return bool(answer.strip()) and not answer.strip().strip(".…").strip()
