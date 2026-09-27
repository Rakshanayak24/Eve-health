"""
Centralized application configuration.

All settings are read from environment variables (see .env.example).
Using pydantic-settings gives us validation + sane defaults for local dev.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    database_url: str = "postgresql://eve_user:eve_password@localhost:5432/eve_healthcare"

    # --- JWT / Auth ---
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # --- Simulated payment provider ---
    # Shared secret the "payment provider" must present when calling our webhook.
    # In a real integration this would be a signature (HMAC) verification instead
    # of a static header, but a shared secret is enough to demonstrate the concept
    # for this assignment.
    webhook_shared_secret: str = "webhook_shared_secret_demo"

    # Deterministic override for the mock payment gateway, useful for tests/demo:
    # if a client sends `force_status` in the payment request we honor it,
    # otherwise we pick success/failure with `payment_success_rate` probability.
    payment_success_rate: float = 0.8

    app_name: str = "EVE Healthcare - Diagnostic Booking Service"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
