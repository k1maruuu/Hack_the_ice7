from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from sqlalchemy.orm import Session
from app.database import get_db
from app.services.route_service import RouteService
from app.services.gars_service import GARSService
from app.schemas.route_schemas import (
    RouteResponse, RouteSearchRequest, RouteSearchResponse,
    RouteCreate
)
# from app.core.security import get_current_user
from app.dependencies import get_current_user
from app.models.models import User
from app.utils.cache import cache_service
from app.tasks import parse_s7_flights_task

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


def _parse_ru_date(date_str: str) -> date:
    """Парсим строку вида '25.11.2025' в date."""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты, нужен ДД.MM.ГГГГ")


def _date_to_ddmmyyyy(d: date) -> str:
    """Перегоняем дату в формат S7 'ДД.MM.ГГГГ'."""
    return d.strftime("%d.%m.%Y")


def _runs_on_date(timetable: Dict[str, Any], target: date) -> bool:
    """
    Проверка: идёт ли рейс по расписанию в указанную дату.

    Поддерживаем кейс:
    - РегулярностьТип == 'ЧислаМесяца'
      и в РегулярностьДниИЧисла указан список чисел через запятую (2,4,6,...).
    В остальных случаях считаем, что рейс ходит каждый день (чтобы не отсеять лишнее).
    """
    reg_type = timetable.get("РегулярностьТип")
    days_str = timetable.get("РегулярностьДниИЧисла") or ""

    if reg_type == "ЧислаМесяца" and days_str:
        try:
            allowed_days = {int(x.strip()) for x in days_str.split(",") if x.strip()}
        except ValueError:
            allowed_days = set()
        return target.day in allowed_days

    # по умолчанию — считаем, что рейс ходит
    return True


def _combine_date_and_time(d: date, timestr: str) -> Optional[str]:
    """
    Берём время из строки '0001-01-01T14:00:00' и клеим его к нужной дате.
    Возвращаем ISO-строку.
    """
    if not timestr:
        return None
    try:
        t = datetime.fromisoformat(timestr).time()
        return datetime.combine(d, t).isoformat()
    except Exception:
        return None


async def _get_s7_flights(origin_city: str, dest_city: str, departure_date: date) -> List[Dict[str, Any]]:
    """
    Достаём рейсы S7 (через Celery + кэш).
    origin_city / dest_city — то, что ожидает твой парсер (например 'Москва', 'Якутск').
    """
    date_out_str = _date_to_ddmmyyyy(departure_date)
    cache_key = f"s7:{origin_city}:{dest_city}:{date_out_str}:one-way"

    cached = await cache_service.get_json(cache_key)
    if cached is not None:
        return cached

    async_result = parse_s7_flights_task.delay(
        origin_city,
        dest_city,
        date_out_str,
        None,  # даты обратно нет
    )
    flights = async_result.get(timeout=120)

    await cache_service.set_json(cache_key, flights, expire=3600)
    return flights


def _find_bus_route(routes: List[Dict[str, Any]], point_a: str, point_b: str) -> Optional[Dict[str, Any]]:
    """
    Ищем маршрут 1С, в описании которого есть обоих пункта (независимо от порядка).
    Пример: 'Якутск Автовокзал — Чурапча с.' или 'Чурапча с. — Якутск Автовокзал'.
    """
    a = point_a.lower()
    b = point_b.lower()

    for r in routes:
        desc = (r.get("Description") or "").lower()
        if a in desc and b in desc:
            return r
    return None


@router.get("/search")
async def search_routes(
    origin: str = Query(..., description="Город отправления (например 'Москва')"),
    destination: str = Query(..., description="Конечный пункт (например 'Чурапча')"),
    departure_date: str = Query(..., description="Дата отправления, формат ДД.MM.ГГГГ (например '25.11.2025')"),
    return_date: Optional[str] = Query(
        None,
        description="Дата обратного выезда, формат ДД.MM.ГГГГ (необязательный параметр)",
    ),
):
    """
    Универсальный поиск маршрутов:

    - Пытается собрать мультимодальную цепочку:
      самолёт (origin → Якутск) + автобус (Якутск/Якутск Автовокзал → destination),
      если такой маршрут существует в 1С.
    - Если указан return_date:
      добавляет обратный автобус (destination → Якутск) и самолёт (Якутск → origin).
    - Если в 1С нет маршрута для destination:
      отдаёт просто рейсы S7 origin → destination (и обратно при return_date).
    """
    dep_date = _parse_ru_date(departure_date)
    ret_date: Optional[date] = _parse_ru_date(return_date) if return_date else None

    origin_norm = origin.strip().lower()
    dest_norm = destination.strip().lower()

    gars_service = GARSService()
    routes_1c = await gars_service.get_filtered_routes_cached()

    # --- Пытаемся найти автобусный маршрут туда (Якутск -> destination) ---
    bus_route_out = (
        _find_bus_route(routes_1c, "якутск автовокзал", dest_norm)
        or _find_bus_route(routes_1c, "якутск", dest_norm)
    )

    # --- Пытаемся найти автобусный маршрут обратно (destination -> Якутск) ---
    bus_route_back: Optional[Dict[str, Any]] = None
    if ret_date is not None:
        bus_route_back = (
            _find_bus_route(routes_1c, dest_norm, "якутск автовокзал")
            or _find_bus_route(routes_1c, dest_norm, "якутск")
        )

    is_yakutsk_origin = origin_norm.startswith("якутск")

    # Если маршрут в 1С есть — строим мультимодальную цепочку
    if bus_route_out is not None:
        # === ТУДА ===

        # Самолёт origin -> Якутск (если origin не Якутск)
        flights_out: List[Dict[str, Any]] = []
        if not is_yakutsk_origin:
            flights_out = await _get_s7_flights(origin_city=origin, dest_city="Якутск", departure_date=dep_date)

        # Автобус Якутск -> destination
        out_route_id = bus_route_out.get("Ref_Key")
        if not out_route_id:
            raise HTTPException(status_code=500, detail="У автобусного маршрута (туда) нет Ref_Key в 1С")

        timetables_out = await gars_service.get_route_timetables_with_cache(out_route_id)
        bus_out_for_date = [t for t in timetables_out if _runs_on_date(t, dep_date)]

        bus_out_options: List[Dict[str, Any]] = []
        for t in bus_out_for_date:
            dep_iso = _combine_date_and_time(dep_date, t.get("ВремяОтправления"))
            arr_iso = _combine_date_and_time(dep_date, t.get("ВремяПрибытия"))
            bus_out_options.append(
                {
                    "timetable": t,
                    "departure_at": dep_iso,
                    "arrival_at": arr_iso,
                }
            )

        outbound = {
            "date": dep_date.isoformat(),
            "segments": [
                {
                    "segment_type": "flight",
                    "provider": "S7",
                    "origin": origin,
                    "destination": "Якутск",
                    "options": flights_out,
                }
                # если origin = Якутск, просто будет пустой список рейсов
                ,
                {
                    "segment_type": "bus",
                    "provider": "GARS_1C",
                    "origin": "Якутск",
                    "destination": destination,
                    "route": bus_route_out,
                    "options": bus_out_options,
                },
            ],
        }

        # === ОБРАТНО (если есть return_date) ===
        ret_part: Optional[Dict[str, Any]] = None
        if ret_date is not None:
            flights_back: List[Dict[str, Any]] = []
            if not is_yakutsk_origin:
                flights_back = await _get_s7_flights(
                    origin_city="Якутск",
                    dest_city=origin,
                    departure_date=ret_date,
                )

            bus_back_options: List[Dict[str, Any]] = []
            if bus_route_back is not None:
                back_route_id = bus_route_back.get("Ref_Key")
                if not back_route_id:
                    raise HTTPException(status_code=500, detail="У автобусного маршрута (обратно) нет Ref_Key в 1С")

                timetables_back = await gars_service.get_route_timetables_with_cache(back_route_id)
                bus_back_for_date = [t for t in timetables_back if _runs_on_date(t, ret_date)]

                for t in bus_back_for_date:
                    dep_iso = _combine_date_and_time(ret_date, t.get("ВремяОтправления"))
                    arr_iso = _combine_date_and_time(ret_date, t.get("ВремяПрибытия"))
                    bus_back_options.append(
                        {
                            "timetable": t,
                            "departure_at": dep_iso,
                            "arrival_at": arr_iso,
                        }
                    )

            ret_part = {
                "date": ret_date.isoformat(),
                "segments": [
                    {
                        "segment_type": "bus",
                        "provider": "GARS_1C",
                        "origin": destination,
                        "destination": "Якутск",
                        "route": bus_route_back,
                        "options": bus_back_options,
                    },
                    {
                        "segment_type": "flight",
                        "provider": "S7",
                        "origin": "Якутск",
                        "destination": origin,
                        "options": flights_back,
                    },
                ],
            }

        return {
            "type": "multimodal",
            "origin": origin,
            "destination": destination,
            "departure_date": dep_date.isoformat(),
            "return_date": ret_date.isoformat() if ret_date else None,
            "outbound": outbound,
            "return": ret_part,
        }

    # --- Fallback: маршрута в 1С нет, только самолёты S7 туда/обратно ---
    flights_out = await _get_s7_flights(origin_city=origin, dest_city=destination, departure_date=dep_date)
    outbound = {
        "date": dep_date.isoformat(),
        "segments": [
            {
                "segment_type": "flight",
                "provider": "S7",
                "origin": origin,
                "destination": destination,
                "options": flights_out,
            }
        ],
    }

    ret_part_flight_only: Optional[Dict[str, Any]] = None
    if ret_date is not None:
        flights_back = await _get_s7_flights(origin_city=destination, dest_city=origin, departure_date=ret_date)
        ret_part_flight_only = {
            "date": ret_date.isoformat(),
            "segments": [
                {
                    "segment_type": "flight",
                    "provider": "S7",
                    "origin": destination,
                    "destination": origin,
                    "options": flights_back,
                }
            ],
        }

    return {
        "type": "flight_only",
        "origin": origin,
        "destination": destination,
        "departure_date": dep_date.isoformat(),
        "return_date": ret_date.isoformat() if ret_date else None,
        "outbound": outbound,
        "return": ret_part_flight_only,
    }

@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение детальной информации о маршруте"""
    route_service = RouteService(db)
    route = route_service.get_route_by_id(route_id)
    
    if not route:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    
    return route

@router.get("/{route_id}/schedule")
async def get_route_schedule(
    route_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение расписания маршрута"""
    try:
        route_service = RouteService(db)
        route = route_service.get_route_by_id(route_id)
        
        if not route:
            raise HTTPException(status_code=404, detail="Маршрут не найден")
        
        gars_service = GARSService()
        schedule = await gars_service.get_route_schedule_with_cache(
            route.gars_id, start_date, end_date
        )
        
        return {"schedule": schedule}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении расписания: {str(e)}")

@router.post("/sync-from-gars")
async def sync_routes_from_gars(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Синхронизация маршрутов с 1С ГАРС"""
    try:
        gars_service = GARSService()
        success = await gars_service.sync_routes(db)
        
        if success:
            return {"message": "Синхронизация выполнена успешно"}
        else:
            raise HTTPException(status_code=500, detail="Ошибка при синхронизации")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка синхронизации: {str(e)}")
