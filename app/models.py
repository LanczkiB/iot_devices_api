from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Metric(StrEnum):
    # Values match the Reading field names.
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"


class Statistic(StrEnum):
    MIN = "min"
    MAX = "max"
    AVG = "avg"


class TemperatureUnit(StrEnum):
    CELSIUS = "C"
    FAHRENHEIT = "F"


@dataclass(frozen=True)
class Reading:
    device_id: int
    measure_time: datetime
    temperature: float  # always stored in Celsius
    humidity: float | None


@dataclass(frozen=True)
class MetricResult:
    value: float | None  # None when the period has no data for this metric
    unit: str


@dataclass(frozen=True)
class DeviceStatistics:
    device_id: int
    period_start: datetime | None
    period_end: datetime | None
    metrics: dict[Metric, MetricResult]

@dataclass(frozen=True)
class StatsResponse:
    statistic: Statistic
    results: list[DeviceStatistics]