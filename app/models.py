# app/models.py
import enum
import random
from sqlalchemy import Column, DateTime, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.schemas import TicketStatusEnum


class AllocationStatus(enum.Enum):
    CNF = "CNF"
    RAC = "RAC"
    WL = "WL"


class SeatMappingCategory(enum.Enum):
    confirmed = "confirmed"
    rac = "rac"


def generate_pnr():
    return random.randint(1000000000, 9999999999)


class SeatMapping(Base):
    __tablename__ = "seat_mapping"
    id = Column(Integer, primary_key=True, index=True)
    seat_number = Column(Integer, unique=True, nullable=False)
    berth_type = Column(String, nullable=False)
    category = Column(Enum(SeatMappingCategory), nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    pnr = Column(Integer, unique=True, nullable=False, default=generate_pnr)
    source = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    status = Column(Enum(TicketStatusEnum),
                    default=TicketStatusEnum.upcoming, nullable=False)
    booking_user_id = Column(Integer, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    passengers = relationship(
        "Passenger", back_populates="ticket", cascade="all, delete-orphan")


class Passenger(Base):
    __tablename__ = "passengers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    ticket = relationship("Ticket", back_populates="passengers")
    berth_allocation = relationship(
        "BerthAllocation", uselist=False, back_populates="passenger", cascade="all, delete-orphan")


class BerthAllocation(Base):
    __tablename__ = "berth_allocation"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(AllocationStatus), nullable=False)  # CNF, RAC, WL
    passenger_id = Column(Integer, ForeignKey("passengers.id"), nullable=False)
    seat_mapping_id = Column(Integer, ForeignKey(
        "seat_mapping.id"), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    passenger = relationship("Passenger", back_populates="berth_allocation")
    seat_mapping = relationship("SeatMapping")
