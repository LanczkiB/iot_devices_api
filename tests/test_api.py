import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    # The context manager runs the lifespan, so the real data/readings.csv is loaded.
    with TestClient(app) as client:
        yield client


def test_defaults(client):
    response = client.get("/stats", params={"metrics": "temperature"})

    assert response.status_code == 200
    body = response.json()
    assert body["statistic"] == "avg"
    assert body["results"] == [
        {
            "device_id": 1,
            "period_start": "2026-07-11T00:00:00Z",
            "period_end": "2026-07-12T00:00:00Z",
            "metrics": {"temperature": {"value": 22.0, "unit": "C"}},
        },
        {
            "device_id": 2,
            "period_start": "2026-07-10T00:00:00Z",
            "period_end": "2026-07-11T00:00:00Z",
            "metrics": {"temperature": {"value": 25.83, "unit": "C"}},
        },
    ]


def test_query_parameters_are_applied(client):
    response = client.get(
        "/stats",
        params={
            "metrics": ["temperature", "humidity"],
            "statistic": "min",
            "device_ids": [1],
            "start": "2026-07-10T00:00:00",  # no timezone: treated as UTC
            "end": "2026-07-11T00:00:00Z",
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["device_id"] == 1
    assert result["period_start"] == "2026-07-10T00:00:00Z"
    assert result["metrics"] == {
        "temperature": {"value": 20.0, "unit": "C"},
        "humidity": {"value": 40.0, "unit": "%"},
    }


def test_fahrenheit_unit(client):
    response = client.get("/stats", params={"metrics": "temperature", "statistic": "max", "device_ids": 2, "unit": "F"})

    assert response.status_code == 200
    assert response.json()["results"][0]["metrics"]["temperature"] == {"value": 80.0, "unit": "F"}


def test_unknown_device_returns_404(client):
    response = client.get("/stats", params={"metrics": "temperature", "device_ids": [1, 9]})

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown device id(s): [9]"}


def test_start_not_before_end_returns_422(client):
    response = client.get(
        "/stats",
        params={"metrics": "temperature", "start": "2026-07-11T00:00:00Z", "end": "2026-07-10T00:00:00Z"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "start must be before end"}


@pytest.mark.parametrize(
    "params",
    [
        {},                                                 # metrics missing
        {"metrics": "pressure"},                            # unknown metric
        {"metrics": "temperature", "statistic": "median"},  # unknown statistic
        {"metrics": "temperature", "unit": "K"},            # unknown unit
        {"metrics": "temperature", "device_ids": "abc"},    # non-integer device id
        {"metrics": "temperature", "start": "yesterday"},   # invalid date
    ],
)
def test_invalid_parameters_return_422(client, params):
    response = client.get("/stats", params=params)

    assert response.status_code == 422