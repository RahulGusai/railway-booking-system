# app/main.py
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, crud
from app.database import SessionLocal, engine, Base
from fastapi.middleware.trustedhost import TrustedHostMiddleware


# Create all tables
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Railway Ticket Reservation API")

# Dependency for DB session


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/v1/tickets/book", response_model=schemas.Ticket)
def book_ticket(ticket: schemas.TicketCreate, db: Session = Depends(get_db)):
    return crud.book_ticket(db, ticket)


@app.post("/api/v1/tickets/cancel/{ticket_id}")
def cancel_ticket(ticket_id: int, db: Session = Depends(get_db)):
    crud.cancel_ticket(db, ticket_id)
    return {"message": "Ticket cancelled and promotions applied successfully."}


@app.get("/api/v1/tickets/booked", response_model=List[schemas.Ticket])
def get_booked_tickets(db: Session = Depends(get_db)):
    return crud.get_booked_tickets(db)


@app.get("/api/v1/tickets/available")
def get_available_seats(db: Session = Depends(get_db)):
    return crud.get_available_seats(db)
