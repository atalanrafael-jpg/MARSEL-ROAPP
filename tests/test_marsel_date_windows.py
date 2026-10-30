from datetime import date

from scripts.marsel_date_windows import build_date_windows


def test_splits_a_full_year_into_windows_no_longer_than_92_days():
    windows = build_date_windows("2026-01-01", "2026-12-31")

    assert windows == [
        (date(2026, 1, 1), date(2026, 4, 2)),
        (date(2026, 4, 3), date(2026, 7, 3)),
        (date(2026, 7, 4), date(2026, 10, 3)),
        (date(2026, 10, 4), date(2026, 12, 31)),
    ]
    assert all((end - start).days + 1 <= 92 for start, end in windows)


def test_keeps_a_range_of_exactly_92_days_in_one_window():
    assert build_date_windows("2026-01-01", "2026-04-02") == [
        (date(2026, 1, 1), date(2026, 4, 2))
    ]


def test_rejects_a_reversed_date_range():
    try:
        build_date_windows("2026-04-03", "2026-04-02")
    except ValueError as exc:
        assert "date_to" in str(exc)
    else:
        raise AssertionError("Expected a reversed date range to be rejected")
