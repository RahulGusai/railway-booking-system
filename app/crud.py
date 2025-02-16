# app/crud.py
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy import func
from app import models, schemas
from app.models import AllocationStatus, SeatMappingCategory


# Capacity constants
MAX_CONFIRMED = 63
MAX_RAC = 9
MAX_WAITING = 10


def get_counts(db: Session):
    confirmed = db.query(models.BerthAllocation).filter(
        models.BerthAllocation.status == AllocationStatus.CNF, models.BerthAllocation.deleted_at.is_(
            None)
    ).count()
    rac = db.query(models.BerthAllocation).filter(
        models.BerthAllocation.status == AllocationStatus.RAC, models.BerthAllocation.deleted_at.is_(
            None)
    ).count()
    waiting = db.query(models.BerthAllocation).filter(
        models.BerthAllocation.status == AllocationStatus.WL, models.BerthAllocation.deleted_at.is_(
            None)
    ).count()
    return confirmed, rac, waiting


def find_available_seat(db: Session, category: SeatMappingCategory, berth_type_preference: str = None):
    """
    Returns an available seat from the SeatMapping table for the given category.
    If berth_type_preference is provided, attempts to return a seat matching that preference.
    Otherwise, returns the first available seat.
    """
    # Get all seat_mapping ids already allocated
    allocated_ids = db.query(models.BerthAllocation.seat_mapping_id).filter(
        models.BerthAllocation.seat_mapping_id.isnot(None),
        models.BerthAllocation.deleted_at.is_(None)
    ).subquery()

    base_query = db.query(models.SeatMapping).filter(
        models.SeatMapping.category == category,
        ~models.SeatMapping.id.in_(allocated_ids)
    ).order_by(models.SeatMapping.seat_number)

    if berth_type_preference:
        seat = base_query.filter(
            models.SeatMapping.berth_type == berth_type_preference).with_for_update().first()
        if seat:
            return seat
    return base_query.with_for_update().first()


def book_ticket(db: Session, ticket_data: schemas.TicketCreate):
    with db.begin():
        _, _, waiting = get_counts(db)
        if waiting + len(ticket_data.passengers) > MAX_WAITING:
            raise HTTPException(
                status_code=400, detail="No tickets available (waiting list full)")

        ticket = models.Ticket(
            source=ticket_data.source,
            destination=ticket_data.destination,
            booking_user_id=ticket_data.booking_user_id,
            status=schemas.TicketStatusEnum.upcoming
        )
        db.add(ticket)
        db.flush()

        for passenger_data in ticket_data.passengers:
            passenger = models.Passenger(
                name=passenger_data.name,
                gender=passenger_data.gender,
                age=passenger_data.age,
                ticket_id=ticket.id
            )
            db.add(passenger)
            db.flush()

            confirmed, rac, waiting = get_counts(db)

            if confirmed < MAX_CONFIRMED:
                if passenger.age >= 60 or is_female_with_children(passenger_data, ticket_data.passengers):
                    seat = find_available_seat(
                        db, SeatMappingCategory.confirmed, berth_type_preference="lower")
                else:
                    seat = find_available_seat(
                        db, SeatMappingCategory.confirmed)

                if not seat:
                    raise HTTPException(
                        status_code=400, detail="No confirmed seat available")

                # If the passenger is not a child (age>=5), allocate a confirmed berth.
                if passenger_data.age >= 5:
                    allocation = models.BerthAllocation(
                        status=AllocationStatus.CNF,
                        passenger_id=passenger.id,
                        seat_mapping_id=seat.id
                    )
                    db.add(allocation)

            elif rac < MAX_RAC:
                seat = find_available_seat(db, SeatMappingCategory.rac)
                if not seat:
                    raise HTTPException(
                        status_code=400, detail="No RAC seat available")

                if passenger_data.age >= 5:
                    allocation = models.BerthAllocation(
                        status=AllocationStatus.RAC,
                        passenger_id=passenger.id,
                        seat_mapping_id=seat.id
                    )
                    db.add(allocation)
            else:
                if passenger_data.age >= 5:
                    allocation = models.BerthAllocation(
                        status=AllocationStatus.WL,
                        passenger_id=passenger.id,
                        seat_mapping_id=None
                    )
                    db.add(allocation)

        db.flush()
        db.refresh(ticket)

    return ticket


def cancel_ticket(db: Session, ticket_id: int):
    ticket = db.query(models.Ticket).filter(
        models.Ticket.id == ticket_id,
        models.Ticket.deleted_at.is_(None)
    ).first()
    if not ticket:
        raise HTTPException(
            status_code=404, detail="Ticket not found or already deleted")

    now = datetime.now(timezone.utc)
    for passenger in ticket.passengers:
        if passenger.berth_allocation and passenger.berth_allocation.deleted_at is None:
            passenger.berth_allocation.deleted_at = now
            db.add(passenger.berth_allocation)
        if passenger.deleted_at is None:
            passenger.deleted_at = now
            db.add(passenger)

    ticket.deleted_at = now
    db.add(ticket)
    db.commit()

    promote_allocations(db)
    return


def promote_allocations(db: Session):
    """
    Promotion logic after cancellation:
      1. While confirmed count is less than MAX_CONFIRMED and there is a RAC ticket available,
         promote RAC to confirmed.
      2. Then, while RAC count is less than MAX_RAC and waiting list entries exist,
         promote waiting list tickets to RAC.
    """
    confirmed, rac, waiting = get_counts(db)

    while confirmed < MAX_CONFIRMED:
        rac_alloc = db.query(models.BerthAllocation).filter(
            models.BerthAllocation.status == AllocationStatus.RAC,
            models.BerthAllocation.deleted_at.is_(None)
        ).order_by(models.BerthAllocation.id.asc()).first()
        if not rac_alloc:
            break
        seat = find_available_seat(db, SeatMappingCategory.confirmed)
        if not seat:
            break
        rac_alloc.status = AllocationStatus.CNF
        rac_alloc.seat_mapping_id = seat.id
        db.commit()
        confirmed, rac, waiting = get_counts(db)

    while rac < MAX_RAC:
        wl_alloc = db.query(models.BerthAllocation).filter(
            models.BerthAllocation.status == AllocationStatus.WL,
            models.BerthAllocation.deleted_at.is_(None)
        ).order_by(models.BerthAllocation.id.asc()).first()
        if not wl_alloc:
            break
        seat = find_available_seat(db, SeatMappingCategory.rac)
        if not seat:
            break
        wl_alloc.status = AllocationStatus.RAC
        wl_alloc.seat_mapping_id = seat.id
        db.commit()
        confirmed, rac, waiting = get_counts(db)


def get_booked_tickets(db: Session):
    tickets = db.query(models.Ticket).filter(
        models.Ticket.deleted_at.is_(None)).all()
    return tickets


def get_available_seats(db: Session):
    confirmed, rac, waiting = get_counts(db)
    return {
        "available_confirmed": MAX_CONFIRMED - confirmed,
        "available_rac": MAX_RAC - rac,
        "available_waiting": MAX_WAITING - waiting
    }


def is_female_with_children(passenger_data, ticket_passengers):
    if passenger_data.gender != "female":
        return False

    no_of_children = 0
    for ticket_passenger in ticket_passengers:
        if ticket_passenger.age < 5:
            no_of_children += 1
    return True if no_of_children > 0 else False
