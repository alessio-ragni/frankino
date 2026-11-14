"""Il secondo controllo: la frase comincia col nome? È l'eco della sua voce?"""

import pytest

from frankino.addressed import called, echo, silent


@pytest.mark.parametrize(
    "text",
    [
        "Franco, che ore sono?",
        "Ehi Franco, mi senti?",
        "Ciao Franchino!",
        "Frankino, metti un timer",
        "ok Franko",
        "Hey Franco, what time is it?",
        "Fraco.",  # storpiato dal trascrittore
        "Frank, tell me a joke",
        "No, Franco, non così",
        "Senti Franco, una cosa",
        "Francò, dimmi",
    ],
)
def test_chiamato(text):
    assert called(text)


@pytest.mark.parametrize(
    "text",
    [
        "Ho visto Franco ieri al mercato",
        "La partita alle nove e mezza",
        "Francesca, vieni a tavola",
        "Il franco svizzero è salito",
        "Fanno la partita domani",
        "Banco di prova",
        "Francia o Spagna?",
        "Ehi ehi ehi Franco",  # troppi saluti davanti
        "",
        "Hello",
    ],
)
def test_non_chiamato(text):
    assert not called(text)


def test_eco():
    said = "Ecco la carbonara, sono cinque passaggi. Buon appetito!"
    assert echo("sono cinque passaggi", said)
    assert echo("Ecco la carbonara, sono cinque passaggi.", said)
    assert not echo("e per quattro persone?", said)
    assert not echo("qualcosa", "")


def test_silenzio():
    assert silent("…") and silent("...") and silent(" … ")
    assert not silent("") and not silent("… ah, ok")
