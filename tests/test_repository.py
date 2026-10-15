from datetime import datetime, timezone

import pytest

from app.models import Reading
from app.repository import ReadingRepository

HEADER = "DeviceId,MeasureTime,Temperature,TempUnit,Humidity\n"


def load(tmp_path, *rows: str) -> list[Reading]:
    csv_file = tmp_path / "readings.csv"
    csv_file.write_text(HEADER + "\n".join(rows) + "\n")
    return ReadingRepository(csv_file).get_all()


def test_parses_celsius_row(tmp_path):
    readings = load(tmp_path, "1,2026-07-10T10:00:00Z,23,C,42")

    assert readings == [
        Reading(
            device_id=1,
            measure_time=datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc),
            temperature=23.0,
            humidity=42.0,
        )
    ]


def test_timestamp_without_timezone_is_treated_as_utc(tmp_path):
    readings = load(tmp_path, "1,2026-07-10T10:00:00,23,C,42")

    assert readings[0].measure_time == datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)


def test_converts_fahrenheit_to_celsius(tmp_path):
    readings = load(tmp_path, "2,2026-07-10T10:00:00Z,77,F,")

    assert readings[0].temperature == pytest.approx(25.0)


def test_empty_humidity_becomes_none(tmp_path):
    readings = load(tmp_path, "2,2026-07-10T10:00:00Z,77,F,")

    assert readings[0].humidity is None


@pytest.mark.parametrize(
    "row",
    [
        "1,2026-07-10T10:00:00Z,23,K,42",       # unknown unit
        "1,2026-07-10T10:00:00Z,warm,C,42",     # non-numeric temperature
        "abc,2026-07-10T10:00:00Z,23,C,42",     # non-numeric device id
        "1,not-a-date,23,C,42",                 # invalid timestamp
    ],
)
def test_invalid_row_raises_error_with_line_number(tmp_path, row):
    with pytest.raises(ValueError, match="line 3"):
        load(tmp_path, "1,2026-07-10T10:00:00Z,23,C,42", row)


def test_missing_column_raises_error(tmp_path):
    csv_file = tmp_path / "readings.csv"
    csv_file.write_text("DeviceId,MeasureTime,Temperature\n1,2026-07-10T10:00:00Z,23\n")

    with pytest.raises(ValueError, match="line 2"):
        ReadingRepository(csv_file)