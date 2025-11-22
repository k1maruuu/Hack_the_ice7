from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.services.gars_service import GARSService

router = APIRouter(
    prefix="/api/v1/gars",
    tags=["gars-routes"],
)


@router.get("/routes")
async def get_gars_routes() -> List[Dict[str, Any]]:
    """
    Берёт маршруты из 1С, фильтрует (без ' С', '2024', 'Тест') и
    кладёт в Redis-кэш, чтобы не дёргать 1С каждый раз.
    """
    service = GARSService()
    routes = await service.get_filtered_routes_cached()
    if routes is None:
        raise HTTPException(status_code=500, detail="Не удалось получить маршруты из 1С")
    return routes
