import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request

from app.models import Reading
from app.repository import ReadingRepository

DATA_PATH = Path(os.getenv("DATA_PATH", "data/readings.csv"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.repository = ReadingRepository.from_csv(DATA_PATH)
    yield

app = FastAPI(title="IOT DEVICES API", lifespan=lifespan)

def get_repository(request: Request) -> ReadingRepository:
    return request.app.state.repository

@app.get("/readings")
def get_readings(repository: ReadingRepository = Depends(get_repository)) -> list[Reading]:
    return repository.get_all()