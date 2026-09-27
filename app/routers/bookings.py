from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=schemas.BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    test = db.query(models.DiagnosticTest).filter(models.DiagnosticTest.id == payload.test_id).first()
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic test not found")

    booking = models.Booking(
        user_id=current_user.id,
        test_id=test.id,
        centre_id=test.centre_id,
        appointment_time=payload.appointment_time,
        amount=test.price,
        status=models.BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/", response_model=schemas.PaginatedBookings)
def list_my_bookings(
    status_filter: models.BookingStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Booking).filter(models.Booking.user_id == current_user.id)
    if status_filter:
        query = query.filter(models.Booking.status == status_filter)

    total = query.count()
    items = (
        query.order_by(models.Booking.created_at.desc()).offset(offset).limit(limit).all()
    )
    return schemas.PaginatedBookings(total=total, limit=limit, offset=offset, items=items)


def _get_owned_booking(db: Session, booking_id: str, current_user: models.User) -> models.Booking:
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != current_user.id:
        # 403, not 404: the booking exists but the caller isn't allowed to see/act on it.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this booking"
        )
    return booking


@router.get("/{booking_id}", response_model=schemas.BookingOut)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_owned_booking(db, booking_id, current_user)


@router.patch("/{booking_id}/cancel", response_model=schemas.BookingOut)
def cancel_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    booking = _get_owned_booking(db, booking_id, current_user)

    if booking.status == models.BookingStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A confirmed (paid) booking cannot be cancelled through this endpoint. "
            "Please contact support for refunds.",
        )
    if booking.status == models.BookingStatus.CANCELLED:
        # Idempotent: cancelling twice is a no-op, not an error.
        return booking

    booking.status = models.BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking
