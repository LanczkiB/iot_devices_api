import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Reading:
    device_id: int
    measure_time: datetime
    temperature: float
    humidity: float | None


def fahrenheit_to_celsius(value: float) -> float:
    return (value - 32) * 5 / 9


class ReadingRepository:
    def __init__(self, path: Path):
        self._readings = []
        with open(path, newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    self._readings.append(_parse_row(row))
                except (KeyError, ValueError) as error:
                    raise ValueError(f"Invalid data in {path}, line {reader.line_num}: {error}") from error

    def get_all(self) -> list[Reading]:
        return list(self._readings)


def _parse_row(row: dict[str, str]) -> Reading:
    temperature = float(row["Temperature"])
    unit = row["TempUnit"].strip().upper()
    if unit == "F":
        temperature = fahrenheit_to_celsius(temperature)
    elif unit != "C":
        raise ValueError(f"unknown temperature unit '{unit}'")

    humidity = row["Humidity"].strip()
    return Reading(
        device_id=int(row["DeviceId"]),
        measure_time=datetime.fromisoformat(row["MeasureTime"]),
        temperature=temperature,
        humidity=float(humidity) if humidity else None,
    )