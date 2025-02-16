# app/seat_mapping_prepopulate.py
from app.database import SessionLocal, engine, Base
from app.models import SeatMapping, SeatMappingCategory


def prepopulate_seat_mapping():
    db = SessionLocal()
    # Check if already populated
    if db.query(SeatMapping).first():
        print("Seat mapping already populated.")
        db.close()
        return

    # Positions:
    #   1: lower
    #   2: middle
    #   3: upper
    #   4: lower  (priority lower berth)
    #   5: middle
    #   6: upper
    #   7: side-lower (for RAC)
    #   8: side-upper
    pattern = [
        ("lower", "confirmed"),
        ("middle", "confirmed"),
        ("upper", "confirmed"),
        ("lower", "confirmed"),
        ("middle", "confirmed"),
        ("upper", "confirmed"),
        ("side-lower", "rac"),
        ("side-upper", "confirmed")
    ]
    seat_number = 1
    bays = 9  # Total seats = 9 * 8 = 72
    for _ in range(bays):
        for berth_type, category in pattern:
            mapping = SeatMapping(
                seat_number=seat_number,
                berth_type=berth_type,
                category=SeatMappingCategory.confirmed if category == "confirmed" else SeatMappingCategory.rac
            )
            db.add(mapping)
            seat_number += 1
    db.commit()
    db.close()
    print("Seat mapping pre-populated.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    prepopulate_seat_mapping()
