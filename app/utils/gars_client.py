import aiohttp
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import asyncio
# from app.core.config import settings
import json
import os

class GARSClient:
    def __init__(self):
        self.base_url  = os.getenv("GARS_BASE_URL")
        self.username  = os.getenv("GARS_USERNAME")
        self.password  = os.getenv("GARS_PASSWORD")
        self.timeout   = int(os.getenv("GARS_TIMEOUT", 30))
        
        # Создание Basic Auth заголовка
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_credentials}"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            try:
                async with session.request(method, url, headers=self._get_headers(), params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"GARS API Error: {response.status} - {await response.text()}")
                        return None
            except Exception as e:
                print(f"Request failed: {e}")
                return None
    
    async def get_routes(self) -> Optional[List[Dict]]:
        """Получение списка маршрутов"""
        params = {"$format": "json"}
        response = await self._make_request("GET", "Catalog_Маршруты", params)
        
        if response and "value" in response:
            return response["value"]
        return None
    
    async def get_route_schedule(self, route_id: str, start_date: date, end_date: date) -> Optional[List[Dict]]:
        """Получение расписания маршрута"""
        filter_query = f"Period ge datetime'{start_date.isoformat()}T00:00:00' and Period le datetime'{end_date.isoformat()}T23:59:59'"
        params = {
            "$filter": filter_query,
            "$format": "json"
        }
        
        response = await self._make_request("GET", "InformationRegister_РасписаниеРейсов", params)
        
        if response and "value" in response:
            return response["value"]
        return None
    
    async def get_prices(self, route_id: str, departure_date: date) -> Optional[List[Dict]]:
        """Получение цен на маршрут"""
        filter_query = f"Date eq datetime'{departure_date.isoformat()}T00:00:00'"
        params = {
            "$filter": filter_query,
            "$format": "json"
        }
        
        response = await self._make_request("GET", "InformationRegister_ДействующиеТарифы", params)
        
        if response and "value" in response:
            return response["value"]
        return None
    
    async def check_seats_availability(self, route_id: str, departure_date: date) -> Optional[Dict]:
        """Проверка доступности мест"""
        filter_query = f"Route eq '{route_id}' and Date eq datetime'{departure_date.isoformat()}T00:00:00'"
        params = {
            "$filter": filter_query,
            "$format": "json"
        }
        
        response = await self._make_request("GET", "InformationRegister_ЗанятостьМест", params)
        
        if response and "value" in response:
            return response["value"]
        return None
    
    async def create_booking(self, booking_data: Dict[str, Any]) -> Optional[Dict]:
        """Создание бронирования в 1С"""
        response = await self._make_request(
            "POST", 
            "Document_ЗаказБилетовИУслуг",
            params={"$format": "json"}
        )
        return response
    
    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Optional[Dict]:
        """Создание билета в 1С"""
        response = await self._make_request(
            "POST",
            "Document_Билет",
            params={"$format": "json"}
        )
        return response

    async def get_route_timetables(self, route_id: str) -> Optional[List[Dict]]:
        """
        Расписания рейсов из Catalog_РейсыРасписания по конкретному маршруту.

        route_id = Ref_Key из Catalog_Маршруты
        """
        params = {
            "$filter": f"Маршрут_Key eq guid'{route_id}'",
            "$format": "json",
            "$expand": "Остановки"
        }

        response = await self._make_request("GET", "Catalog_РейсыРасписания", params)

        if response and "value" in response:
            return response["value"]
        return None