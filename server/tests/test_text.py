from frankino.text import Splitter, sentences


def test_a_pezzi_suona_come_tutto_insieme():
    whole = "Ciao. Oggi piove a Milano! Domani? Sole, forse; vedremo: dipende."
    s = Splitter()
    out = []
    for i in range(0, len(whole), 3):
        out += s.feed(whole[i : i + 3])
    out += s.flush()
    assert out == sentences(whole)


def test_niente_markdown_in_bocca():
    assert sentences("**Pronto**: ecco.\n- uno\n- due") == ["Pronto:", "ecco.", "uno", "due"]


def test_una_frase_senza_fine_non_resta_muta():
    s = Splitter(max_chars=20)
    assert s.feed("parola " * 10)
