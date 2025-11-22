# app/schemas/s7_schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List


class S7SearchRequest(BaseModel):
    origin: str = Field(..., description="Город или IATA-код вылета (напр. 'Москва' или 'MOW')")
    destination: str = Field(..., description="Город или IATA-код прилёта (напр. 'Якутск' или 'YKS')")
    date_out: str = Field(..., description="Дата вылета в формате ДД.ММ.ГГГГ")
    date_back: Optional[str] = Field(None, description="Дата возврата в формате ДД.ММ.ГГГГ или null")


class S7Flight(BaseModel):
    flight_no: str
    dep_time: str
    arr_time: str
    price_rub: int
    booking_url: str