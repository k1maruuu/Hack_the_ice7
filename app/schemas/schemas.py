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
    birthday: date
    sex: str
    email_user: Optional[EmailStr] = None
    email_corporate: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    tg_name: str
    position_employee: str
    role: UserRole

    # новые необязательные HR-поля
    city: Optional[str] = None
    work_experience: Optional[int] = None
    hierarchy_status: Optional[str] = None

    june: Optional[int] = None
    july: Optional[int] = None
    august: Optional[int] = None
    september: Optional[int] = None
    october: Optional[int] = None

    accreditation: Optional[str] = None
    training: Optional[str] = None
    vacation: Optional[str] = None
    sick_leave: Optional[bool] = None
    rebuke: Optional[bool] = None
    activity: Optional[bool] = None

    burn_out_score: Optional[int] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    birthday: Optional[date] = None
    sex: Optional[str] = None
    email_user: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    tg_name: Optional[str] = None
    position_employee: Optional[str] = None
    role: Optional[UserRole] = None

    city: Optional[str] = None
    work_experience: Optional[int] = None
    hierarchy_status: Optional[str] = None

    june: Optional[int] = None
    july: Optional[int] = None
    august: Optional[int] = None
    september: Optional[int] = None
    october: Optional[int] = None

    accreditation: Optional[str] = None
    training: Optional[str] = None
    vacation: Optional[str] = None
    sick_leave: Optional[bool] = None
    rebuke: Optional[bool] = None
    activity: Optional[bool] = None

    burn_out_score: Optional[int] = None
    
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


class ChatMessageBotBase(BaseModel):
    role: str
    content: str

class ChatMessageBotCreate(ChatMessageBotBase):
    pass

class ChatMessageBotInDB(ChatMessageBotBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatSessionBotBase(BaseModel):
    title: Optional[str] = None

class ChatSessionBotCreate(ChatSessionBotBase):
    pass

class ChatSessionBotInDB(ChatSessionBotBase):
    id: int
    user_id: int
    created_at: datetime
    messages: List[ChatMessageBotInDB] = []
    
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    model: str = "gemma3:4b"
    messages: List[ChatMessageBotBase]
    session_id: Optional[int] = None



