# iot_devices_api

A small REST API that loads IoT sensor readings from a CSV file and returns statistics about them.
It is built with Python and FastAPI.

## How to run

Requirements: Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs on http://localhost:8000.
Interactive documentation is available at http://localhost:8000/docs (automatically created by FastApi based on main.py and models.py).

By default the app loads `data/readings.csv`.
To use a different file, set the `DATA_PATH` environment variable:

```bash
DATA_PATH=/path/to/other.csv uvicorn app.main:app
```

## How to run the tests

```bash
pytest
```

## The endpoint

There is one endpoint: `GET /stats`.

| Parameter    | Required | Values                     | Default                     |
|--------------|----------|----------------------------|-----------------------------|
| `metrics`    | yes      | `temperature`, `humidity`  | none                        |
| `statistic`  | no       | `min`, `max`, `avg`        | `avg`                       |
| `device_ids` | no       | integers                   | all devices                 |
| `start`      | no       | ISO 8601 date or datetime  | see "Default period" below  |
| `end`        | no       | ISO 8601 date or datetime  | see "Default period" below  |
| `unit`       | no       | `C`, `F`                   | `C`                         |

Parameters that take more than one value are repeated:
`?metrics=temperature&metrics=humidity&device_ids=1&device_ids=2`.

### Example 1: defaults

```
GET /stats?metrics=temperature&metrics=humidity
```

```json
{
  "statistic": "avg",
  "results": [
    {
      "device_id": 1,
      "period_start": "2026-07-11T00:00:00Z",
      "period_end": "2026-07-12T00:00:00Z",
      "metrics": {
        "temperature": {"value": 22.0, "unit": "C"},
        "humidity": {"value": 44.0, "unit": "%"}
      }
    },
    {
      "device_id": 2,
      "period_start": "2026-07-10T00:00:00Z",
      "period_end": "2026-07-11T00:00:00Z",
      "metrics": {
        "temperature": {"value": 25.83, "unit": "C"},
        "humidity": {"value": null, "unit": "%"}
      }
    }
  ]
}
```

### Example 2: maximum temperature in Fahrenheit for one day

```
GET /stats?metrics=temperature&statistic=max&device_ids=1&device_ids=2&start=2026-07-10&end=2026-07-11&unit=F
```

```json
{
  "statistic": "max",
  "results": [
    {
      "device_id": 1,
      "period_start": "2026-07-10T00:00:00Z",
      "period_end": "2026-07-11T00:00:00Z",
      "metrics": {"temperature": {"value": 89.6, "unit": "F"}}
    },
    {
      "device_id": 2,
      "period_start": "2026-07-10T00:00:00Z",
      "period_end": "2026-07-11T00:00:00Z",
      "metrics": {"temperature": {"value": 80.0, "unit": "F"}}
    }
  ]
}
```

### Errors

| Status | When                                                                   |
|--------|------------------------------------------------------------------------|
| 404    | A requested device does not exist in the data.                         |
| 422    | A parameter is missing or invalid, or `start` is not before `end`.     |

All errors use the same format as FastAPI's built-in validation errors:

```json
{
  "detail": [
    {
      "type": "unknown_device",
      "loc": ["query", "device_ids"],
      "msg": "Unknown device id(s): [9]",
      "input": [9]
    }
  ]
}
```

## Design decisions

### Structure

The code has three layers:

- `app/repository.py` reads the CSV file into a list of readings.
- `app/service.py` filters the readings and computes the statistics.
- `app/main.py` defines the HTTP endpoint and the error handlers.

The service does not depend on FastAPI.
This makes it easy to test the logic without starting a web server.

### Loading the data

The CSV file is loaded once, when the app starts.
The readings are kept in memory.
The data is small and does not change, so a database is not needed.

If any row in the CSV is invalid, the app does not start.
The error message includes the line number of the bad row.
I chose to fail early instead of silently skipping rows, because skipped rows would make the statistics wrong without anyone noticing.

### Temperature units

The CSV contains temperatures in both Celsius and Fahrenheit.
When the file is loaded, I convert every Fahrenheit value to Celsius.
This way all temperatures are stored in one unit, and different devices can be compared.

The response is in Celsius by default.
If the request asks for Fahrenheit (`unit=F`), the result is converted after the statistic is calculated.
This gives the same result as converting each value first, because the conversion is linear.

### Default period ("latest available data")

If neither `start` nor `end` is given, the API uses the latest day of data for each device.
A day is a calendar day in UTC.

For example, the latest reading of device 1 is on 2026-07-11, so its period is that day.
The latest reading of device 2 is on 2026-07-10, so its period is that day.

I chose a whole day instead of only the single latest reading, because min, max and average are not useful for one value.
I chose a separate period per device, because devices may stop reporting at different times.
Each result includes `period_start` and `period_end`, so the client can see which period was used.

### Date range

- `start` is inclusive and `end` is exclusive. So `start=2026-07-10&end=2026-07-11` means exactly one day.
- You can give only `start` or only `end`. The other side is then open.
- Dates without a timezone are treated as UTC. This applies to the query parameters and to the CSV timestamps.

### Missing values

Device 2 has no humidity values.
In this case the API returns `"value": null` for that metric instead of an error.
The other metrics are still returned.

If a period contains no readings at all, every metric value is `null`.

### Validation

FastAPI validates the parameter types and the allowed values (for example `statistic` must be `min`, `max` or `avg`).
The service also checks two things:

- Every requested device must exist. If not, the API returns 404.
- `start` must be before `end`. If not, the API returns 422.

### Why `metrics` is required

The task does not define a default metric.
I made `metrics` required, so the client always says explicitly what it wants.
Also `metrics` is the only part of the assignment where `not specified` option is not mentioned so I chose to make it required.

## Limitations and possible improvements

- The data is kept in memory and filtered on every request. This is fine for a small file. For large data I would use a database (filtering and aggregation would move to SQL - repository.py would query it, and service.py would be thinner).
- Changes to the CSV file are only picked up after a restart.
- There is no authentication.