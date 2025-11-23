from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.route_models import Route, RouteSegment
from app.schemas.route_schemas import RouteCreate, RouteSegmentBase

class RouteService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_route_by_id(self, route_id: int) -> Optional[Route]:
        """Получение маршрута по ID"""
        return self.db.query(Route).filter(Route.id == route_id).first()
    
    def get_route_by_gars_id(self, gars_id: str) -> Optional[Route]:
        """Получение маршрута по GARS ID"""
        return self.db.query(Route).filter(Route.gars_id == gars_id).first()
    
    def create_route(self, route_create: RouteCreate) -> Route:
        """Создание маршрута"""
        db_route = Route(
            gars_id=route_create.gars_id,
            code=route_create.code,
            name=route_create.name,
            description=route_create.description,
            duration_minutes=route_create.duration_minutes
        )
        self.db.add(db_route)
        self.db.commit()
        self.db.refresh(db_route)
        return db_route
    
    def create_route_segment(self, route_id: int, segment_data: RouteSegmentBase) -> RouteSegment:
        """Создание сегмента маршрута"""
        db_segment = RouteSegment(
            route_id=route_id,
            transport_type=segment_data.transport_type,
            departure_point=segment_data.departure_point,
            arrival_point=segment_data.arrival_point,
            departure_time=segment_data.departure_time,
            arrival_time=segment_data.arrival_time,
            carrier_name=segment_data.carrier_name,
            flight_number=segment_data.flight_number,
            order_index=segment_data.order_index
        )
        self.db.add(db_segment)
        self.db.commit()
        self.db.refresh(db_segment)
        return db_segment
    
    def get_active_routes(self, skip: int = 0, limit: int = 100) -> List[Route]:
        """Получение активных маршрутов"""
        return self.db.query(Route).filter(Route.status == "active").offset(skip).limit(limit).all()
