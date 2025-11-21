from app.utils.password_utils import password_check
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.schemas.schemas import UserCreate, UserInDB, UserUpdate
from app.crud import get_user_by_email, create_user, update_user, search_users as search_users_crud, get_notifications
from app.database import get_db
from app.dependencies import get_current_user, get_admin_user
from app.models.models import User, UserRole
from app.logging_config import logger

router = APIRouter(prefix="/users", tags=["users"])
limiter = Limiter(key_func=get_remote_address)

"""POST"""
"""СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ"""
@router.post("/", response_model=UserInDB)
@limiter.limit("50/hour")
async def create_user_endpoint(
    request: Request, 
    user: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: UserInDB = Depends(get_admin_user)
):
    logger.info(f"Admin {current_user.email_user} is creating user: {user.full_name}")
    
    db_user = get_user_by_email(db, email=user.email_user)
    if db_user:
        logger.warning(f"Ошибка в создании аккаунта: Email {user.email_user} уже зарегистрирован")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if (password_check(user)):
        logger.info(f"Аккаунт {user.email_user} создан админом: {current_user.email_user}")
        new_user = create_user(db=db, user=user)
        return new_user
    else:
        logger.warning(f"Ошибка создания пользователя - {user.full_name}: Слабый пароль")
        raise HTTPException(status_code=403, detail="Weak password")

"""GET"""
"""ИНФОРМАЦИЯ О СЕБЕ"""
@router.get("/me", response_model=UserInDB)
@limiter.limit("30/minute")
def read_users_me(
    request: Request,
    current_user: UserInDB = Depends(get_current_user)
):
    return current_user

"""ПОИСК СОТРУДНИКА"""
@router.get("/", response_model=List[UserInDB])
@limiter.limit("30/minute")
def search_users(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    full_name: Optional[str] = Query(None, description="Поиск по полному имени (имя, фамилия, отчество)"),
    role: Optional[UserRole] = Query(None, description="Фильтр по роли (admin, manager, user)"),
    sex: Optional[str] = Query(None, description="Фильтр по полу (М или Ж)"),
    skip: int = 0,
    limit: int = 10
):
    # Собираем параметры фильтрации
    filters = {
        "full_name": full_name,
        "role": role,
        "sex": sex
    }
    logger.info(f"User {current_user.email_user} searching users with filters: {filters}")
    users = search_users_crud(db, **filters)
    logger.info(f"User {current_user.email_user} found {len(users)} users")
    return users[skip:skip + limit]

"""ПРОСМОТР СОТРУДНИКА"""
@router.get("/{user_id}", response_model=UserInDB)
@limiter.limit("50/minute")
def get_user(
    request: Request, 
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)  # Доступно для всех авторизованных пользователей
):
    logger.info(f"User {current_user.email_user} viewed profile of user ID {user_id}")
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

"""PUT"""
"""РЕДАКТИРОВАНИЕ ПОЛЬЗОВАТЕЛЯ"""
@router.put("/{user_id}", response_model=UserInDB)
@limiter.limit("30/minute")
def update_user_endpoint(
    request: Request, 
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_user)
):
    logger.info(f"Admin {current_user.email_user} updating user ID {user_id}")
    updated_user = update_user(db, user_id=user_id, user_update=user_update)
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

"""DELETE"""
"""УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ"""
@router.delete("/{user_id}", response_model=dict)
@limiter.limit("10/hour")
def delete_user(
    request: Request, 
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_admin_user)
):
    logger.info(f"Admin {current_user.email_user} deleting user ID {user_id}")
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    logger.info(f"User {db_user.email_user} deleted by admin {current_user.email_user}")
    return {"message": "User deleted successfully"}

"""УВЕДОМЛЕНИЯ"""
@router.get("/me/notifications", response_model=List[dict])
@limiter.limit("30/minute")
def get_my_notifications(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    notifications = get_user_notifications(db, user_id=current_user.id)
    return [{"id": n.id, "message": n.message, "is_read": n.is_read, "created_at": n.created_at} for n in notifications]