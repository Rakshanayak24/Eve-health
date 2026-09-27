"""
Simulated payment gateway.

No real money or external provider is involved. `simulate_gateway_call`
stands in for "the HTTP call we'd make to Stripe/Razorpay/etc" and just
returns SUCCESS or FAILED, either deterministically (if the caller forces
an outcome - handy for tests/demos) or randomly using a configurable
success rate.
"""
import random
import uuid

from app.config import settings
from app.models import PaymentStatus


def new_provider_reference() -> str:
    """A unique id representing 'the payment attempt at the provider'."""
    return f"sim_{uuid.uuid4().hex}"


def simulate_gateway_call(force_status: PaymentStatus | None = None) -> PaymentStatus:
    if force_status is not None:
        return force_status
    return (
        PaymentStatus.SUCCESS
        if random.random() < settings.payment_success_rate
        else PaymentStatus.FAILED
    )
