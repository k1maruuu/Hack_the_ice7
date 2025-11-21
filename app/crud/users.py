from sqlalchemy.orm import Session
from passlib.context import CryptContext 
from fastapi import HTTPException
from dotenv import load_dotenv
from app.logging_config import logger
from app.schemas.schemas import UserCreate, UserUpdate
from app.models.models import User, Notification, UserRole
from typing import Optional
"""ФУНКЦИИ"""

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email_user == email).first()



def get_user(db: Session, user_id: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user





def create_user(db: Session, user: UserCreate) -> User:
    logger.info(f"Attempting to create user: {user.full_name}")
    logger.info(f"Попытка создания аккаунта для: {user.full_name}")
    hashed_password = pwd_context.hash(user.password)

    db_user = User(
        full_name=user.full_name,
        sex=user.sex,
        email_user=user.email_user,
        hashed_password=hashed_password,
        phone_number=user.phone_number,
        role=user.role,
        is_active=True,
        login_attempts=0,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"Создан новый пользователь: {db_user.email_user}, ID: {db_user.id}")
    return db_user




def update_user(db: Session, user_id: int, user_update: UserUpdate):
    NOTIFY_FIELDS = {
        "full_name": "Ваше имя обновлено",
        "phone_number": "Ваш номер телефона обновлён",
        "email_user": "Ваш email обновлён",
        "sex": "Ваш пол обновлён",
    }

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    update_data = user_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_user, field, value)
        if field in NOTIFY_FIELDS:
            create_notification(db, db_user.id, f"{NOTIFY_FIELDS[field]}: {value}")

    db.commit()
    db.refresh(db_user)
    return db_user




def search_users(db: Session, full_name: str = None, role: UserRole = None, sex: str = None):
    try:
        query = db.query(User)

        # Фильтрация по full_name
        if full_name:
            query = query.filter(User.full_name.ilike(f"%{full_name}%"))

        # Фильтрация по роли
        if role:
            query = query.filter(User.role == role)

        # Фильтрация по полу
        if sex:
            if sex not in ["М", "Ж"]:
                raise HTTPException(status_code=422, detail="Invalid sex value. Must be 'М' or 'Ж'")
            query = query.filter(User.sex == sex)

        result = query.all()
        print(f"Search results for filters {locals()}: {[u.full_name for u in result]}")  # Отладка
        return result
    except Exception as e:
        print(f"Search error for filters {locals()}: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Error processing filters: {str(e)}")



def authenticate_user(db: Session, email: str, password: str):
    logger.info(f"Authentication attempt for email: {email}")
    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        logger.warning(f"Authentication failed for {email}: User not found or inactive")
        return False
    if not pwd_context.verify(password, user.hashed_password):
        user.login_attempts += 1
        logger.warning(f"Authentication failed for {email}: Incorrect password, attempts: {user.login_attempts}")
        if user.login_attempts >= 5:
            user.is_active = False
            logger.error(f"User {email} blocked due to too many login attempts")
            if not has_block_notification(db, user.id):
                create_notification(db, user.id, "Ваш аккаунт заблокирован из-за неудачных попыток входа.")
                if user.role == "admin":
                    admins = db.query(User).filter(User.role == "admin").all()
                    for admin in admins:
                        if not has_block_notification(db, admin.id):
                            create_notification(db, admin.id, f"Пользователь {user.email_user} заблокирован из-за неудачных попыток входа.")
        db.commit()
        return False
    user.login_attempts = 0 
    db.commit()
    logger.info(f"User {email} authenticated successfully")
    return user 
    

"""УВЕДОМЛЕНИЯ"""
