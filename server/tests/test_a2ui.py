import pytest

from frankino.a2ui import Invalid, check


def test_mette_versione_e_catalogo():
    out = check('[{"createSurface": {"surfaceId": "x"}}]', "v0.9.1")
    assert out == [
        {
            "version": "v0.9.1",
            "createSurface": {
                "surfaceId": "x",
                "catalogId": "https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json",
            },
        }
    ]


@pytest.mark.parametrize(
    "bad",
    [
        [],
        "non json",
        [{"boh": {}}],
        [{"updateComponents": {"surfaceId": "x", "components": []}}],
        [{"updateComponents": {"surfaceId": "x", "components": [{"id": "root"}]}}],
        [{"deleteSurface": {}}],
    ],
)
def test_rifiuta_la_spazzatura(bad):
    with pytest.raises(Invalid):
        check(bad, "v0.9.1")
