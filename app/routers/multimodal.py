from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import date, datetime

from app.utils.cache import cache_service
from app.tasks import parse_s7_flights_task
from app.services.gars_service import GARSService

router = APIRouter(
    prefix="/api/v1/multimodal",
    tags=["multimodal"],
)


def _parse_ru_date(date_str: str) -> date:
    """Парсим строку вида '25.11.2025' в date."""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты, нужен ДД.MM.ГГГГ")


def _date_to_ddmmyyyy(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _runs_on_date(timetable: Dict[str, Any], target: date) -> bool:
    """
    Очень упрощённая проверка регулярности:
    если РегулярностьТип == 'ЧислаМесяца', берём числа из РегулярностьДниИЧисла
    и проверяем совпадение дня.
    В остальных случаях считаем, что рейс ходит каждый день.
    """
    reg_type = timetable.get("РегулярностьТип")
    days_str = timetable.get("РегулярностьДниИЧисла") or ""

    if reg_type == "ЧислаМесяца" and days_str:
        try:
            allowed_days = {int(x.strip()) for x in days_str.split(",") if x.strip()}
        except ValueError:
            allowed_days = set()
        return target.day in allowed_days

    return True


def _combine_date_and_time(d: date, timestr: str) -> Optional[str]:
    """Берём время из '0001-01-01T14:00:00' и наклеиваем на нужную дату."""
    if not timestr:
        return None
    try:
        t = datetime.fromisoformat(timestr).time()
        return datetime.combine(d, t).isoformat()
    except Exception:
        return None


async def _get_s7_flights(origin_city: str, transfer_city: str, departure_date: date) -> List[Dict[str, Any]]:
    """
    Достаём рейсы S7 (через Celery + кэш),
    формат даты для S7: ДД.MM.ГГГГ.
    """
    date_out_str = _date_to_ddmmyyyy(departure_date)
    cache_key = f"s7:{origin_city}:{transfer_city}:{date_out_str}:one-way"

    cached = await cache_service.get_json(cache_key)
    if cached is not None:
        return cached

    # Запускаем задачу Celery
    async_result = parse_s7_flights_task.delay(
        origin_city,
        transfer_city,
        date_out_str,
        None,
    )
    flights = async_result.get(timeout=120)

    await cache_service.set_json(cache_key, flights, expire=3600)
    return flights


@router.get("/search-moscow-churapcha")
async def search_moscow_churapcha(
    origin: str = Query("Москва", description="город вылета (пока ожидается 'Москва')"),
    destination: str = Query("Чурапча", description="конечный пункт (пока ожидается 'Чурапча')"),
    departure_date: str = Query(..., description="Дата отправления, формат ДД.MM.ГГГГ (например '25.11.2025')"),
):
    """
    Комбинированный маршрут:

    1) Самолёт S7: Москва → Якутск (через твой S7-парсер).
    2) Автобус 1С: 'Якутск Автовокзал — Чурапча с.' из Catalog_Маршруты,
       сверенный с его расписанием из Catalog_РейсыРасписания на указанную дату.

    Возвращаем JSON с:
    - flights: рейсы самолёта
    - bus_route: объект маршрута из 1С
    - bus_options: варианты автобусов (расписание, время отправления/прибытия в ISO)
    """
    # пока жёстко завязываемся именно на Чурапчу
    if destination.lower().strip().startswith("чурапча") is False:
        raise HTTPException(status_code=400, detail="Сейчас комбинируем только маршрут до Чурапчи")

    dep_date = _parse_ru_date(departure_date)

    # 1. Рейсы S7 Москва → Якутск
    flights = await _get_s7_flights(origin_city=origin, transfer_city="Якутск", departure_date=dep_date)

    # 2. Находим маршрут автобуса Якутск Автовокзал — Чурапча с. в 1С
    gars_service = GARSService()
    routes = await gars_service.get_filtered_routes_cached()

    bus_route: Optional[Dict[str, Any]] = None
    for r in routes:
        name = (r.get("Description") or "")
        if "Якутск Автовокзал" in name and "Чурапча" in name:
            bus_route = r
            break

    if not bus_route:
        raise HTTPException(
            status_code=404,
            detail="Автобусный маршрут 'Якутск Автовокзал — Чурапча' не найден в 1С"
        )

    route_id = bus_route.get("Ref_Key")
    if not route_id:
        raise HTTPException(status_code=500, detail="У маршрута из 1С нет Ref_Key")

    # 3. Берём расписания рейсов этого маршрута из Catalog_РейсыРасписания
    timetables = await gars_service.get_route_timetables_with_cache(route_id)

    # 4. Фильтруем по дате
    buses_for_date = [t for t in timetables if _runs_on_date(t, dep_date)]

    bus_options: List[Dict[str, Any]] = []
    for t in buses_for_date:
        dep_iso = _combine_date_and_time(dep_date, t.get("ВремяОтправления"))
        arr_iso = _combine_date_and_time(dep_date, t.get("ВремяПрибытия"))
        bus_options.append(
            {
                "timetable": t,
                "departure_at": dep_iso,
                "arrival_at": arr_iso,
            }
        )

    return {
        "date": dep_date.isoformat(),
        "origin": origin,
        "destination": destination,
        "flights": flights,
        "bus_route": bus_route,
        "bus_options": bus_options,
    }
