# app/schemas.py
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

# Enums for Pydantic validation


class TicketStatusEnum(str, Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    cancelled = "cancelled"
    completed = "completed"


class AllocationStatusEnum(str, Enum):
    CNF = "CNF"
    RAC = "RAC"
    WL = "WL"

# Passenger schemas


class PassengerBase(BaseModel):
    name: str
    gender: str
    age: int


class PassengerCreate(PassengerBase):
    pass


class Passenger(PassengerBase):
    id: int

    class Config:
        orm_mode = True

# Ticket schemas


class TicketBase(BaseModel):
    source: Optional[str]
    destination: Optional[str]
    booking_user_id: int


class TicketCreate(TicketBase):
    passengers: List[PassengerCreate]


class Ticket(TicketBase):
    id: int
    pnr: int
    status: TicketStatusEnum
    passengers: List[Passenger]

    class Config:
        orm_mode = True


# Berth Allocation schema (if needed)
class BerthAllocation(BaseModel):
    id: int
    status: AllocationStatusEnum
    seat_number: Optional[int]
    berth_type: Optional[str]
    passenger_id: int

    class Config:
        orm_mode = True
