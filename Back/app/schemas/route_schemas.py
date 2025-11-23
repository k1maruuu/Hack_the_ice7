from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

class TransportType(str, Enum):
    BUS = "bus"
    FLIGHT = "flight"
    TRAIN = "train"
    RIVER = "river"

class RouteStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"

# === Маршруты ===

class RouteSegmentBase(BaseModel):
    transport_type: TransportType
    departure_point: str
    arrival_point: str
    departure_time: datetime
    arrival_time: datetime
    carrier_name: Optional[str] = None
    flight_number: Optional[str] = None
    order_index: int

class RouteSegmentResponse(RouteSegmentBase):
    id: int
    
    class Config:
        from_attributes = True

class RouteBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: Optional[int] = None

class RouteCreate(RouteBase):
    code: str
    gars_id: str

class RouteResponse(RouteBase):
    id: int
    code: str
    gars_id: str
    status: RouteStatus
    duration_minutes: Optional[int]
    segments: List[RouteSegmentResponse]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# === Поиск ===

class RouteSearchRequest(BaseModel):
    departure_point: str
    arrival_point: str
    departure_date: date
    return_date: Optional[date] = None
    passenger_count: int = Field(default=1, ge=1, le=9)
    transport_types: Optional[List[TransportType]] = None

class RouteSearchResponse(BaseModel):
    route: RouteResponse
    available_seats: int
    min_price: Decimal
    currency: str = "RUB"
    schedule: List[Dict[str, Any]]

# === Бронирование ===

class PassengerBase(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birth_date: date
    document_type: str
    document_number: str

class PassengerCreate(PassengerBase):
    pass

class PassengerResponse(PassengerBase):
    id: int
    
    class Config:
        from_attributes = True

class BookingBase(BaseModel):
    route_id: int
    departure_date: date
    return_date: Optional[date] = None
    passenger_count: int = Field(ge=1, le=9)
    contact_phone: str
    contact_email: str

class BookingCreate(BookingBase):
    passengers: List[PassengerCreate]

class BookingResponse(BookingBase):
    id: int
    user_id: int
    gars_booking_id: Optional[str]
    status: str
    total_amount: Optional[Decimal]
    created_at: datetime
    updated_at: Optional[datetime]
    route: RouteResponse
    passengers: List[PassengerResponse]
    
    class Config:
        from_attributes = True

# === Тикеты ===

class TicketResponse(BaseModel):
    id: int
    booking_id: int
    gars_ticket_id: Optional[str]
    ticket_number: str
    qr_code: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
