from datetime import datetime
from typing import Optional, List
import enum

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models import BookingStatus, PaymentStatus


class PaymentOutcome(str, enum.Enum):
    """Terminal outcomes accepted from the simulator or provider webhook."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# ---------- Auth ----------
class UserSignup(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Diagnostic Centres & Tests ----------
class DiagnosticTestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)


class DiagnosticTestOut(BaseModel):
    id: str
    centre_id: str
    name: str
    price: float

    model_config = ConfigDict(from_attributes=True)


class DiagnosticCentreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)
    tests: Optional[List[DiagnosticTestCreate]] = None


class DiagnosticCentreOut(BaseModel):
    id: str
    name: str
    location: str
    tests: List[DiagnosticTestOut] = []

    model_config = ConfigDict(from_attributes=True)


class Paginated(BaseModel):
    total: int
    limit: int
    offset: int


class PaginatedCentres(Paginated):
    items: List[DiagnosticCentreOut]


# ---------- Bookings ----------
class BookingCreate(BaseModel):
    test_id: str
    appointment_time: datetime


class BookingOut(BaseModel):
    id: str
    user_id: str
    test_id: str
    centre_id: str
    appointment_time: datetime
    amount: float
    status: BookingStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedBookings(Paginated):
    items: List[BookingOut]


# ---------- Payments ----------
class PaymentCreate(BaseModel):
    booking_id: str
    # Optional test hook: force a deterministic outcome instead of the random
    # simulator. Only intended for local testing/demoing, not a real gateway.
    force_status: Optional[PaymentOutcome] = None


class PaymentOut(BaseModel):
    id: str
    booking_id: str
    amount: float
    status: PaymentStatus
    provider_reference: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookPayload(BaseModel):
    event_id: str = Field(description="Unique id of this webhook event, used for idempotency")
    provider_reference: str = Field(description="References the Payment created earlier")
    status: PaymentOutcome


class WebhookResponse(BaseModel):
    received: bool
    duplicate: bool
    booking_status: Optional[BookingStatus] = None
