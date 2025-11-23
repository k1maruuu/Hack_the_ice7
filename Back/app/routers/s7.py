# app/routers/s7.py

from fastapi import APIRouter, HTTPException
from typing import List


from app.utils.cache import cache_service
from app.tasks import parse_s7_flights_task

from app.schemas.s7_schemas import S7SearchRequest, S7Flight
from app.services.s7_parser import run_s7_search

router = APIRouter(
    prefix="/s7",
    tags=["s7-parser"],
)


@router.post("/search", response_model=List[S7Flight])
async def search_s7_flights(body: S7SearchRequest):
    cache_key = f"s7:{body.origin}|{body.destination}|{body.date_out}|{body.date_back or '-'}"

    # 1. проверяем кэш
    cached = await cache_service.get_json(cache_key)
    if cached is not None:
        return cached

    # 2. Celery
    async_result = parse_s7_flights_task.delay(
        body.origin,
        body.destination,
        body.date_out,
        body.date_back,
    )
    flights = async_result.get(timeout=120)

    # 3. кладём в кэш
    await cache_service.set_json(cache_key, flights, expire=3600)

    return flights
