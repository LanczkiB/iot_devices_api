import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from app.models import Metric, Statistic, StatsResponse, TemperatureUnit
from app.repository import ReadingRepository
from app.service import InvalidQueryError, UnknownDeviceError, compute_statistics

DATA_PATH = Path(os.getenv("DATA_PATH", "data/readings.csv"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.repository = ReadingRepository(DATA_PATH)
    yield

app = FastAPI(title="IOT DEVICES API", lifespan=lifespan)

def get_repository(request: Request) -> ReadingRepository:
    return request.app.state.repository


@app.exception_handler(UnknownDeviceError)
async def unknown_device_handler(request: Request, error: UnknownDeviceError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(InvalidQueryError)
async def invalid_query_handler(request: Request, error: InvalidQueryError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(error)})


@app.get("/stats")
def get_stats(
    metrics: Annotated[list[Metric], Query(description="One or more metrics to include")],
    statistic: Statistic = Statistic.AVG,
    device_ids: Annotated[list[int] | None, Query(description="Devices to include; all if omitted")] = None,
    start: Annotated[datetime | None, Query(description="Inclusive start (ISO 8601); UTC if no timezone")] = None,
    end: Annotated[datetime | None, Query(description="Exclusive end (ISO 8601); UTC if no timezone")] = None,
    unit: TemperatureUnit = TemperatureUnit.CELSIUS,
    repository: ReadingRepository = Depends(get_repository),
) -> StatsResponse:
    results = compute_statistics(
        repository.get_all(),
        metrics=metrics,
        statistic=statistic,
        device_ids=device_ids,
        start=_as_utc(start),
        end=_as_utc(end),
        unit=unit,
    )
    return StatsResponse(statistic=statistic, results=results)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)