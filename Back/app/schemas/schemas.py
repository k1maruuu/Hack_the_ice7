from pydantic import BaseModel, EmailStr, constr
from typing import Optional, List
from enum import Enum
from datetime import datetime, date

"""СТРУКТУРЫ ДАННЫХ"""

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


"""КЛАССЫ USER"""

class UserBase(BaseModel):
    full_name: str
    sex: Optional[str] = None
    email_user: EmailStr
    phone_number: str
    role: UserRole

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    sex: Optional[str] = None
    email_user: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    role: Optional[UserRole] = None
    
class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: int
    is_active: bool
    login_attempts: int
    created_at: datetime

    class Config:
        from_attributes  = True  


"""КЛАССЫ TOKENA"""

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


"""Suppor"""
class SupportMessageBase(BaseModel):
    content: str

class SupportMessageResponse(BaseModel):
    id: int
    sender_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class SupportChatResponse(BaseModel):
    id: int
    user_id: int
    messages: List[SupportMessageResponse] = []

    class Config:
        from_attributes = True

class SupportChatShort(BaseModel):
    id: int
    user_id: int
    user_full_name: str
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None

"""booking"""
class BookingCreate(BaseModel):
    # для локальных маршрутов будем сохранять подпись
    origin: Optional[str] = None
    destination: Optional[str] = None

    departure_date: date
    return_date: Optional[date] = None

    price_rub: int


class BookingResponse(BaseModel):
    id: int
    status: str
    total_amount: float
    passenger_count: Optional[int] = None

    departure_date: date
    return_date: Optional[date] = None

    contact_phone: str
    contact_email: str

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
