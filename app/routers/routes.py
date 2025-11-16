from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
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

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])

@router.get("/search", response_model=List[RouteSearchResponse])
async def search_routes(
    departure_point: str = Query(..., description="Точка отправления"),
    arrival_point: str = Query(..., description="Точка прибытия"),
    departure_date: date = Query(..., description="Дата отправления"),
    return_date: Optional[date] = Query(None, description="Дата возвращения"),
    passenger_count: int = Query(1, ge=1, le=9, description="Количество пассажиров"),
    transport_types: Optional[List[str]] = Query(None, description="Типы транспорта"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск мультимедийных маршрутов"""
    try:
        search_request = RouteSearchRequest(
            departure_point=departure_point,
            arrival_point=arrival_point,
            departure_date=departure_date,
            return_date=return_date,
            passenger_count=passenger_count,
            transport_types=transport_types
        )
        
        gars_service = GARSService()
        routes = await gars_service.search_multimodal_routes(search_request)
        
        # Конвертация в формат ответа
        response = []
        for route_info in routes:
            # Здесь должна быть логика преобразования данных из 1С в наши модели
            # Пока упрощенная версия
            route_response = RouteSearchResponse(
                route=route_info["route_data"],  # Нужно преобразовать
                available_seats=route_info["availability"].get("AvailableSeats", 0),
                min_price=route_info["min_price"],
                schedule=route_info["schedule"]
            )
            response.append(route_response)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске маршрутов: {str(e)}")

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
