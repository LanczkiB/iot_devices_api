from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from statistics import mean

from app.models import DeviceStatistics, Metric, MetricResult, Reading, Statistic, TemperatureUnit
from app.units import celsius_to_fahrenheit

AGGREGATIONS = {Statistic.MIN: min, Statistic.MAX: max, Statistic.AVG: mean}

class UnknownDeviceError(Exception):
    def __init__(self, device_ids: list[int]):
        self.device_ids = device_ids
        super().__init__(f"Unknown device id(s): {device_ids}")


class InvalidQueryError(Exception):
    pass

def compute_statistics(
    readings: list[Reading],
    metrics: list[Metric],
    statistic: Statistic = Statistic.AVG,
    device_ids: list[int] | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    unit: TemperatureUnit = TemperatureUnit.CELSIUS,
) -> list[DeviceStatistics]:
    """Compute one statistic per device and metric.

    The period is [start, end). Without start and end, each device's latest day (UTC) is used.
    start and end must be timezone-aware.
    """
    if start and end and start >= end:
        raise InvalidQueryError("start must be before end")
    
    readings_by_device = _group_by_device(readings)
    selected_ids = _select_devices(readings_by_device, device_ids)

    results = []
    for device_id in selected_ids:
        device_readings = readings_by_device[device_id]
        if start is None and end is None:
            period_start, period_end = _latest_day(device_readings)
        else:
            period_start, period_end = start, end

        in_period = [r for r in device_readings if _in_period(r.measure_time, period_start, period_end)]
        results.append(
            DeviceStatistics(
                device_id=device_id,
                period_start=period_start,
                period_end=period_end,
                metrics={metric: _aggregate(in_period, metric, statistic, unit) for metric in metrics},
            )
        )
    return results


def _group_by_device(readings: list[Reading]) -> dict[int, list[Reading]]:
    grouped = defaultdict(list)
    for reading in readings:
        grouped[reading.device_id].append(reading)
    return grouped


def _select_devices(readings_by_device: dict[int, list[Reading]], device_ids: list[int] | None) -> list[int]:
    if not device_ids:
        return sorted(readings_by_device)
    unknown = sorted(set(device_ids) - readings_by_device.keys())
    if unknown:
        raise UnknownDeviceError(unknown)
    return sorted(set(device_ids))


def _latest_day(readings: list[Reading]) -> tuple[datetime, datetime]:
    latest = max(r.measure_time for r in readings).astimezone(timezone.utc)
    day_start = datetime.combine(latest.date(), time.min, tzinfo=timezone.utc)
    return day_start, day_start + timedelta(days=1)


def _in_period(moment: datetime, start: datetime | None, end: datetime | None) -> bool:
    return (start is None or moment >= start) and (end is None or moment < end)


def _aggregate(readings: list[Reading], metric: Metric, statistic: Statistic, unit: TemperatureUnit) -> MetricResult:
    unit_label = "%" if metric == Metric.HUMIDITY else unit
    values = [getattr(r, metric) for r in readings if getattr(r, metric) is not None]
    if not values:
        return MetricResult(value=None, unit=unit_label)

    result = AGGREGATIONS[statistic](values)
    if metric == Metric.TEMPERATURE and unit == TemperatureUnit.FAHRENHEIT:
        # Converting after aggregation is safe: the conversion is linear and increasing.
        result = celsius_to_fahrenheit(result)
    return MetricResult(value=round(result, 2), unit=unit_label)