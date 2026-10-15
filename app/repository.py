import csv
from datetime import datetime, timezone
from pathlib import Path

from app.models import Reading
from app.units import fahrenheit_to_celsius

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

    measure_time = datetime.fromisoformat(row["MeasureTime"])
    if measure_time.tzinfo is None:
        measure_time = measure_time.replace(tzinfo=timezone.utc)

    humidity_text = row["Humidity"].strip()
    humidity = float(humidity_text) if humidity_text else None
    if humidity is not None and not 0 <= humidity <= 100:
        raise ValueError(f"humidity {humidity} is outside 0-100%")

    return Reading(
        device_id=int(row["DeviceId"]),
        measure_time=measure_time,
        temperature=temperature,
        humidity=humidity,
    )