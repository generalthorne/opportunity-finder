from datetime import date

import pytest

from opportunity_intelligence.extraction.page_extractor import parse_date


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("November 20, 2026", date(2026, 11, 20)),
        ("Nov 20, 2026", date(2026, 11, 20)),
        ("20 November 2026", date(2026, 11, 20)),
        ("20 Nov 2026", date(2026, 11, 20)),
        ("2026-11-20", date(2026, 11, 20)),
        ("11/20/2026", date(2026, 11, 20)),
        ("November 2026", date(2026, 11, 1)),
        ("", None),
        (None, None),
    ]
)
def test_parse_date(value, expected):
    assert parse_date(value) == expected