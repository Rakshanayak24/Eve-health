import logging

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.services.payment_service import new_provider_reference, simulate_gateway_call

logger = logging.getLogger("eve.payments")

router = APIRouter(prefix="/payments", tags=["Payments"])


def _apply_outcome(booking: models.Booking, payment: models.Payment, outcome: models.PaymentStatus):
    payment.status = outcome
    if outcome == models.PaymentStatus.SUCCESS:
        booking.status = models.BookingStatus.CONFIRMED
    elif outcome == models.PaymentStatus.FAILED:
        booking.status = models.BookingStatus.FAILED


@router.post("/", response_model=schemas.PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Simulates charging the user for a booking.

    In a real integration this would call out to a gateway and return
    immediately with a PENDING payment, with the final state arriving later
    via the webhook. To keep this assignment's happy-path simple we resolve
    the outcome synchronously here *and* still expose /payments/webhook/ as
    the channel a real provider would use for async confirmation.
    """
    booking = db.query(models.Booking).filter(models.Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this booking"
        )

    if booking.status != models.BookingStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking is not payable in its current status ({booking.status.value})",
        )

    payment = models.Payment(
        booking_id=booking.id,
        amount=booking.amount,
        status=models.PaymentStatus.PENDING,
        provider_reference=new_provider_reference(),
    )
    db.add(payment)
    db.flush()

    outcome = simulate_gateway_call(
        force_status=(
            models.PaymentStatus(payload.force_status.value)
            if payload.force_status is not None
            else None
        )
    )
    _apply_outcome(booking, payment, outcome)

    db.commit()
    db.refresh(payment)
    logger.info(
        "payment.processed",
        extra={"booking_id": booking.id, "payment_id": payment.id, "outcome": outcome.value},
    )
    return payment


@router.post("/webhook/", response_model=schemas.WebhookResponse)
def payment_webhook(
    payload: schemas.WebhookPayload,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None),
):
    """
    Receives async payment-status updates from the (simulated) provider.

    Idempotency strategy (two layers, since webhooks can arrive concurrently
    as well as be naively retried later):

    1. `event_id` uniqueness: every distinct webhook delivery has its own
       event_id. We record every event_id we've successfully processed in
       `webhook_events`. If we see it again, we short-circuit and return the
       previously-known outcome without touching booking/payment state.
    2. A DB-level UNIQUE constraint on `webhook_events.event_id` backs this
       up: if two identical requests race each other, only one INSERT wins
       and the other is caught as an IntegrityError and treated as a
       duplicate too, so we never double-apply a payment.

    We also refuse to move a payment/booking that has already reached a
    terminal state to a *different* outcome from a stale/out-of-order
    webhook, to avoid corrupting booking state.
    """
    if settings.webhook_shared_secret and x_webhook_secret != settings.webhook_shared_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook credentials")

    existing_event = (
        db.query(models.WebhookEvent).filter(models.WebhookEvent.event_id == payload.event_id).first()
    )
    if existing_event:
        booking_status = None
        if existing_event.payment_id:
            payment = db.query(models.Payment).filter(models.Payment.id == existing_event.payment_id).first()
            if payment:
                booking_status = payment.booking.status
        return schemas.WebhookResponse(received=True, duplicate=True, booking_status=booking_status)

    payment = (
        db.query(models.Payment)
        .filter(models.Payment.provider_reference == payload.provider_reference)
        .first()
    )
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No payment found for the given provider_reference",
        )

    booking = payment.booking

    outcome = models.PaymentStatus(payload.status.value)
    already_terminal = payment.status in (models.PaymentStatus.SUCCESS, models.PaymentStatus.FAILED)
    if already_terminal and payment.status != outcome:
        # Conflicting/out-of-order update after a terminal state: don't corrupt
        # existing state, but still record that we saw this event so a retry
        # of *this same* event_id is recognized as a duplicate later.
        logger.warning(
            "payment.webhook_conflict",
            extra={
                "payment_id": payment.id,
                "current_status": payment.status.value,
                "incoming_status": outcome.value,
            },
        )
    elif not already_terminal:
        _apply_outcome(booking, payment, outcome)

    event = models.WebhookEvent(
        event_id=payload.event_id,
        payment_id=payment.id,
        payload=payload.model_dump_json(),
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race to a concurrent identical webhook delivery: treat as a
        # duplicate rather than an error.
        db.rollback()
        return schemas.WebhookResponse(received=True, duplicate=True, booking_status=booking.status)

    db.refresh(booking)
    return schemas.WebhookResponse(received=True, duplicate=False, booking_status=booking.status)
