from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Numeric, Boolean, Text, Date
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime

class TransportType(str, PyEnum):
    BUS = "bus"        # Автобус
    FLIGHT = "flight"  # Самолет
    TRAIN = "train"    # ЖД
    RIVER = "river"    # Речной транспорт

class RouteStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"

class Route(Base):
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, index=True)
    gars_id = Column(String, unique=True, index=True)  # ID из 1С
    code = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(Enum(RouteStatus), default=RouteStatus.ACTIVE)
    duration_minutes = Column(Integer)  # Общее время в пути
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    segments = relationship("RouteSegment", back_populates="route", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="route")

class RouteSegment(Base):
    __tablename__ = "route_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    gars_id = Column(String)  # ID из 1С
    
    transport_type = Column(Enum(TransportType), nullable=False)
    departure_point = Column(String, nullable=False)
    arrival_point = Column(String, nullable=False)
    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime, nullable=False)
    
    carrier_name = Column(String)
    flight_number = Column(String)  # Номер рейса/поезда/автобуса
    
    order_index = Column(Integer, nullable=False)  # Порядок следования
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    route = relationship("Route", back_populates="segments")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    gars_booking_id = Column(String)  # ID бронирования в 1С
    
    status = Column(String, default="pending")  # pending, confirmed, cancelled
    total_amount = Column(Numeric(10, 2), nullable=False)
    passenger_count = Column(Integer, default=1)
    
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date)  # Для туда-обратно
    
    contact_phone = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    route = relationship("Route", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
    passengers = relationship("Passenger", back_populates="booking", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="booking", cascade="all, delete-orphan")

class Passenger(Base):
    __tablename__ = "passengers"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    gars_passenger_id = Column(String)  # ID в 1С
    
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    middle_name = Column(String)
    birth_date = Column(Date, nullable=False)
    document_type = Column(String, nullable=False)  # passport, birth_certificate
    document_number = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    booking = relationship("Booking", back_populates="passengers")

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    gars_ticket_id = Column(String, unique=True)  # ID билета в 1С
    
    ticket_number = Column(String, unique=True, index=True)
    qr_code = Column(Text)
    status = Column(String, default="active")  # active, used, refunded
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    booking = relationship("Booking", back_populates="tickets")
