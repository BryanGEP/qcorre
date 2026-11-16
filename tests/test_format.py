"""Tests de los textos de tiempo."""

import pytest

from qcorre import i18n
from qcorre.ui.format import running_for, short_duration

M, H, D = 60, 3600, 86400


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "<1m"),
        (59, "<1m"),
        (41 * M, "41m"),
        (2 * H + 14 * M, "2h 14m"),
        (2 * H + 5 * M, "2h 05m"),
        (3 * D + 4 * H + 30 * M, "3d 4h"),
        (-5, "<1m"),
    ],
)
def test_short_duration(seconds, expected):
    assert short_duration(seconds) == expected


def test_running_for_en_los_dos_idiomas():
    previous = i18n.get_language()
    try:
        i18n.set_language("es")
        assert running_for(3 * D + 4 * H) == "lleva 3 días"
        assert running_for(1 * D) == "lleva 1 día"
        assert running_for(5 * H) == "lleva 5 horas"
        assert running_for(30) == "lleva 1 minuto"
        i18n.set_language("en")
        assert running_for(3 * D) == "running for 3 days"
        assert running_for(1 * H) == "running for 1 hour"
    finally:
        i18n.set_language(previous)
