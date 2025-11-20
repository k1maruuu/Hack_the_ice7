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