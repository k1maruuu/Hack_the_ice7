from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from app.utils.gars_client import GARSClient
from app.utils.cache import cache_service
from app.models.route_models import Route, RouteSegment, TransportType
from app.schemas.route_schemas import RouteSearchRequest
import json

class GARSService:
    def __init__(self):
        self.client = GARSClient()
    
    async def sync_routes(self, db) -> bool:
        """Синхронизация маршрутов с 1С"""
        try:
            routes_data = await self.client.get_routes()
            if not routes_data:
                return False
            
            for route_data in routes_data:
                # Обработка и сохранение маршрута в БД
                route = Route(
                    gars_id=route_data.get("Ref_Key"),
                    code=route_data.get("Code"),
                    name=route_data.get("Description"),
                    description=route_data.get("Комментарий", "")
                )
                db.add(route)
            
            db.commit()
            return True
        except Exception as e:
            print(f"Error syncing routes: {e}")
            db.rollback()
            return False
    
    async def get_route_schedule_with_cache(self, route_id: str, start_date: date, end_date: date) -> Optional[List[Dict]]:
        """Получение расписания с кэшированием"""
        cache_key = f"schedule:{route_id}:{start_date}:{end_date}"
        
        # Попытка получить из кэша
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        
        # Получение из 1С
        schedule_data = await self.client.get_route_schedule(route_id, start_date, end_date)
        if schedule_data:
            # Сохранение в кэш на 30 минут
            await cache_service.set(cache_key, json.dumps(schedule_data), ttl=1800)
        
        return schedule_data
    
    async def search_multimodal_routes(self, search_request: RouteSearchRequest) -> List[Dict[str, Any]]:
        """Поиск мультимодальных маршрутов"""
        # Логика поиска комбинаций маршрутов
        # Это сложная логика, которая должна комбинировать разные типы транспорта
        
        routes = []
        
        # Получение всех активных маршрутов
        all_routes = await self.client.get_routes()
        if not all_routes:
            return routes
        
        # Фильтрация по типу транспорта и маршруту
        for route_data in all_routes:
            # Здесь должна быть логика поиска комбинаций
            # Пока простой пример фильтрации
            if self._matches_route_criteria(route_data, search_request):
                route_info = await self._enrich_route_info(route_data, search_request)
                if route_info:
                    routes.append(route_info)
        
        return routes
    
    def _matches_route_criteria(self, route_data: Dict, search_request: RouteSearchRequest) -> bool:
        """Проверка соответствия маршрута критериям поиска"""
        # Простая логика проверки - нужно расширить для мультимодальных маршрутов
        route_name = route_data.get("Description", "").lower()
        departure = search_request.departure_point.lower()
        arrival = search_request.arrival_point.lower()
        
        return departure in route_name and arrival in route_name
    
    async def _enrich_route_info(self, route_data: Dict, search_request: RouteSearchRequest) -> Optional[Dict[str, Any]]:
        """Обогащение информацией о маршруте"""
        route_id = route_data.get("Ref_Key")
        if not route_id:
            return None
        
        # Получение расписания
        schedule = await self.get_route_schedule_with_cache(
            route_id, 
            search_request.departure_date,
            search_request.departure_date + timedelta(days=7)
        )
        
        # Получение цен
        prices = await self.client.get_prices(route_id, search_request.departure_date)
        
        # Проверка доступности мест
        availability = await self.client.check_seats_availability(route_id, search_request.departure_date)
        
        return {
            "route_data": route_data,
            "schedule": schedule or [],
            "prices": prices or [],
            "availability": availability or {},
            "min_price": min([p.get("Price", 0) for p in prices]) if prices else 0
        }
