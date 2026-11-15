"""The second check: does the sentence start with the name? Is it the echo of his voice?"""

import pytest

from frankino.addressed import called, echo, silent, stopped


@pytest.mark.parametrize(
    "text",
    [
        "Franco, che ore sono?",
        "Ehi Franco, mi senti?",
        "Ciao Franchino!",
        "Frankino, metti un timer",
        "ok Franko",
        "Hey Franco, what time is it?",
        "Fraco.",  # misspelled by the transcriber
        "Frank, tell me a joke",
        "No, Franco, non così",
        "Senti Franco, una cosa",
        "Francò, dimmi",
    ],
)
def test_called(text):
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
        "Ehi ehi ehi Franco",  # too many greetings first
        "",
        "Hello",
    ],
)
def test_not_called(text):
    assert not called(text)


def test_echo():
    said = "Ecco la carbonara, sono cinque passaggi. Buon appetito!"
    assert echo("sono cinque passaggi", said)
    assert echo("Ecco la carbonara, sono cinque passaggi.", said)
    assert not echo("e per quattro persone?", said)
    assert not echo("qualcosa", "")


def test_silence():
    assert silent("…") and silent("...") and silent(" … ")
    assert not silent("") and not silent("… ah, ok")


@pytest.mark.parametrize(
    "text", ["Franco, stop", "basta", "grazie", "ok grazie mille", "Franco basta così", "lascia stare"]
)
def test_stopped(text):
    assert stopped(text)


@pytest.mark.parametrize("text", ["basta pasta per stasera", "metti un timer", "grazie, mi dici che ore sono?", "ok"])
def test_not_stopped(text):
    assert not stopped(text)
