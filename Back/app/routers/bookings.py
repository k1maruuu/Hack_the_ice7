from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import User
from app.models.route_models import Booking, Route, RouteStatus
from app.schemas.schemas import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Локальная покупка билета:
    1) создаём простой маршрут в таблице routes
    2) привязываем к нему Booking (чтобы не падал foreign key)
    """

    # подпись маршрута для истории
    if payload.origin and payload.destination:
        route_name = f"{payload.origin} — {payload.destination}"
    else:
        route_name = "Локальный маршрут"

    # создаём Route (минимально, без GARS)
    new_route = Route(
        gars_id=None,
        code=None,
        name=route_name,
        description="Локальный маршрут, созданный через веб-интерфейс",
        status=RouteStatus.ACTIVE,
        duration_minutes=None,
    )
    db.add(new_route)
    db.flush()  # получаем new_route.id без коммита

    # создаём Booking, теперь route_id указывает на реально существующий маршрут
    booking = Booking(
        user_id=current_user.id,
        route_id=new_route.id,
        gars_booking_id=None,
        status="pending",  # потом можно менять на confirmed/cancelled
        total_amount=payload.price_rub,
        passenger_count=1,
        departure_date=payload.departure_date,
        return_date=payload.return_date,
        contact_phone=current_user.phone_number,
        contact_email=current_user.email_user,
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/my", response_model=List[BookingResponse])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return bookings
