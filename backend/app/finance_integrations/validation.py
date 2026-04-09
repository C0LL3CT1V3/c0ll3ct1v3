
"""Strict checks when finance integrations run in production."""

from __future__ import annotations

from typing import Iterable

from ..config import settings


def _is_production() -> bool:
    return settings.app_env.strip().lower() == "production"


def _require(errors: list[str], key: str, value: str) -> None:
    if not value.strip():
        errors.append(f"Missing required setting: {key}.")


def _validate_retention(errors: list[str], values: Iterable[tuple[str, int]]) -> None:
    for key, value in values:
        if value <= 0:
            errors.append(f"{key} must be a positive integer.")


def validate_finance_production_config() -> list[str]:
    errors: list[str] = []
    if not settings.finance_integrations_enabled:
        return errors
    if not _is_production():
        return errors

    if settings.plaid_env.strip().lower() != "production":
        errors.append("PLAID_ENV must be 'production' in production deployments.")
    _require(errors, "PLAID_CLIENT_ID", settings.plaid_client_id)
    _require(errors, "PLAID_SECRET", settings.plaid_secret)
    _require(errors, "PLAID_WEBHOOK_URL", settings.plaid_webhook_url)
    if "sandbox" in settings.plaid_webhook_url.strip().lower():
        errors.append("PLAID_WEBHOOK_URL must not point to sandbox domains.")
    if settings.plaid_link_mode.strip().lower() not in ("stub", "api"):
        errors.append("PLAID_LINK_MODE must be 'stub' or 'api'.")

    if settings.square_env.strip().lower() != "production":
        errors.append("SQUARE_ENV must be 'production' in production deployments.")
    if settings.square_base_url.strip() != "https://connect.squareup.com/v2":
        errors.append("SQUARE_BASE_URL must be https://connect.squareup.com/v2")
    using_oauth = bool(settings.square_application_id or settings.square_application_secret)
    if using_oauth and (not settings.square_application_id or not settings.square_application_secret):
        errors.append("Set both SQUARE_APPLICATION_ID and SQUARE_APPLICATION_SECRET for OAuth mode.")
    if not using_oauth and not settings.square_access_token:
        errors.append("Set SQUARE_ACCESS_TOKEN or Square OAuth credentials.")
    _require(errors, "SQUARE_WEBHOOK_SIGNATURE_KEY", settings.square_webhook_signature_key)
    _require(errors, "SQUARE_WEBHOOK_URL", settings.square_webhook_url)

    _require(errors, "ENCRYPTION_KEY_ID", settings.encryption_key_id)
    _validate_retention(
        errors,
        (
            ("DATA_RETENTION_RAW_WEBHOOK_DAYS", settings.data_retention_raw_webhook_days),
            ("DATA_RETENTION_APP_LOG_DAYS", settings.data_retention_app_log_days),
            ("DATA_RETENTION_AUDIT_LOG_DAYS", settings.data_retention_audit_log_days),
        ),
    )

    if not settings.finance_mfa_admin_enforced:
        errors.append("FINANCE_MFA_ADMIN_ENFORCED must be true in production.")
    if not settings.finance_mfa_consumer_enforced:
        errors.append("FINANCE_MFA_CONSUMER_ENFORCED should be true in production.")
    if not settings.finance_mfa_step_up_for_plaid_link:
        errors.append("FINANCE_MFA_STEP_UP_FOR_PLAID_LINK should be true in production.")
    if settings.mfa_max_age_seconds <= 0:
        errors.append("MFA_MAX_AGE_SECONDS must be a positive integer.")
    methods = {m.strip().lower() for m in settings.finance_mfa_methods_allowed.split(",") if m.strip()}
    if not methods.intersection({"totp", "webauthn", "sms", "push"}):
        errors.append("FINANCE_MFA_METHODS_ALLOWED must include totp, webauthn, sms, or push.")

    return errors
