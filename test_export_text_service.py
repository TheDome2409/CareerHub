from jobagent.services.export_text_service import (
    normalize_export_items,
    normalize_export_text,
    repair_common_mojibake,
)


def test_normalize_export_text_preserves_correct_umlauts():
    assert (
        normalize_export_text("Mögliche Einsatzfelder")
        == "Mögliche Einsatzfelder"
    )
    assert normalize_export_text("für") == "für"


def test_normalize_export_text_does_not_convert_ascii_umlauts():
    assert (
        normalize_export_text("Moegliche Einsatzfelder")
        == "Moegliche Einsatzfelder"
    )
    assert normalize_export_text("fuer") == "fuer"


def test_normalize_export_text_repairs_common_mojibake():
    assert (
        normalize_export_text("MÃ¶gliche Einsatzfelder")
        == "Mögliche Einsatzfelder"
    )
    assert repair_common_mojibake("fÃ¼r") == "für"


def test_normalize_export_text_handles_none_and_whitespace():
    assert normalize_export_text(None) == ""
    assert (
        normalize_export_text(" A\u00a0B  \t C\n\n\n\nD ")
        == "A B C\n\nD"
    )


def test_normalize_export_text_normalizes_typographic_characters():
    assert (
        normalize_export_text("A – B — C …")
        == "A - B - C ..."
    )


def test_normalize_export_items_filters_empty_items():
    assert normalize_export_items(
        [
            " Mögliche Einsatzfelder ",
            "",
            None,
            "fuer",
        ]
    ) == [
        "Mögliche Einsatzfelder",
        "fuer",
    ]
