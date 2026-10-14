from datetime import datetime, timezone

import pytest

from app.models import Metric, Reading, Statistic, TemperatureUnit
from app.service import InvalidQueryError, UnknownDeviceError, compute_statistics
from app.units import fahrenheit_to_celsius


def utc(day: int, hour: int = 0) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


# Same data as the sample CSV, already normalized to Celsius.
READINGS = [
    Reading(1, utc(10, 10), 23.0, 42.0),
    Reading(1, utc(10, 14), 32.0, 45.0),
    Reading(1, utc(10, 18), 20.0, 40.0),
    Reading(1, utc(11, 10), 22.0, 44.0),
    Reading(2, utc(10, 10), fahrenheit_to_celsius(77), None),
    Reading(2, utc(10, 12), fahrenheit_to_celsius(80), None),
]


def test_defaults_use_average_over_each_devices_latest_day():
    results = compute_statistics(READINGS, metrics=[Metric.TEMPERATURE])

    assert [r.device_id for r in results] == [1, 2]
    assert (results[0].period_start, results[0].period_end) == (utc(11), utc(12))
    assert results[0].metrics[Metric.TEMPERATURE].value == 22.0
    assert (results[1].period_start, results[1].period_end) == (utc(10), utc(11))
    assert results[1].metrics[Metric.TEMPERATURE].value == 25.83


@pytest.mark.parametrize(
    ("statistic", "expected"),
    [(Statistic.MIN, 20.0), (Statistic.MAX, 32.0), (Statistic.AVG, 25.0)],
)
def test_statistics(statistic, expected):
    results = compute_statistics(
        READINGS, metrics=[Metric.TEMPERATURE], statistic=statistic, device_ids=[1], start=utc(10), end=utc(11)
    )

    assert results[0].metrics[Metric.TEMPERATURE].value == expected


def test_period_includes_start_and_excludes_end():
    results = compute_statistics(
        READINGS, metrics=[Metric.TEMPERATURE], statistic=Statistic.MAX, device_ids=[1], start=utc(10, 10), end=utc(10, 14)
    )

    assert results[0].metrics[Metric.TEMPERATURE].value == 23.0  # the 14:00 reading (32.0) is excluded


def test_open_ended_period():
    results = compute_statistics(
        READINGS, metrics=[Metric.TEMPERATURE], statistic=Statistic.MAX, device_ids=[1], start=utc(10, 15)
    )

    assert results[0].period_end is None
    assert results[0].metrics[Metric.TEMPERATURE].value == 22.0


def test_filters_devices_and_ignores_duplicates():
    results = compute_statistics(READINGS, metrics=[Metric.TEMPERATURE], device_ids=[2, 2])

    assert [r.device_id for r in results] == [2]


def test_unknown_device_raises_error():
    with pytest.raises(UnknownDeviceError) as error:
        compute_statistics(READINGS, metrics=[Metric.TEMPERATURE], device_ids=[1, 9])

    assert error.value.device_ids == [9]


def test_start_not_before_end_raises_error():
    with pytest.raises(InvalidQueryError):
        compute_statistics(READINGS, metrics=[Metric.TEMPERATURE], start=utc(11), end=utc(10))


def test_metric_without_data_returns_none():
    results = compute_statistics(READINGS, metrics=[Metric.TEMPERATURE, Metric.HUMIDITY], device_ids=[2])

    humidity = results[0].metrics[Metric.HUMIDITY]
    assert humidity.value is None
    assert humidity.unit == "%"


def test_converts_result_to_fahrenheit():
    results = compute_statistics(
        READINGS, metrics=[Metric.TEMPERATURE], statistic=Statistic.MAX, device_ids=[2], unit=TemperatureUnit.FAHRENHEIT
    )

    temperature = results[0].metrics[Metric.TEMPERATURE]
    assert temperature.value == 80.0
    assert temperature.unit == TemperatureUnit.FAHRENHEIT