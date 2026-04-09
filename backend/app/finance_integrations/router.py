
"""Finance integration HTTP routes."""

from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from ..config import settings
from .audit import audit_event
from .deps import require_finance_auth
from .finance_auth import FinanceAuthContext, create_step_up_challenge, require_recent_mfa, verify_step_up_challenge
from .finance_models import (
    PlaidDisconnectRequest,
    PlaidDisconnectResponse,
    PlaidLinkTokenRequest,
    PlaidLinkTokenResponse,
    PlaidPublicTokenExchangeRequest,
    PlaidPublicTokenExchangeResponse,
    StepUpChallengeRequest,
    StepUpChallengeResponse,
    StepUpVerifyRequest,
    StepUpVerifyResponse,
    WebhookAckResponse,
)
from .finance_auth import parse_allowed_methods
from .plaid_client import create_link_token, exchange_public_token, remove_item
from .webhook_utils import dedupe_event, parse_json_body, redact_payload, verify_square_signature

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.get("/healthz")
def finance_healthcheck() -> dict[str, str]:
    return {"status": "ok", "finance": "enabled" if settings.finance_integrations_enabled else "disabled"}


@router.post("/auth/step-up/challenge", response_model=StepUpChallengeResponse)
def mfa_challenge(
    payload: StepUpChallengeRequest,
    auth_context: FinanceAuthContext = Depends(require_finance_auth),
) -> StepUpChallengeResponse:
    if settings.auth_provider.lower() == "auth0" and not settings.finance_demo_auth:
        raise HTTPException(
            status_code=501,
            detail="Use Auth0 step-up authentication in the client and pass bearer token with MFA claims.",
        )
    challenge_id = create_step_up_challenge(user_id=auth_context.user_id, reason=payload.reason)
    return StepUpChallengeResponse(challenge_id=challenge_id, allowed_methods=parse_allowed_methods())


@router.post("/auth/step-up/verify", response_model=StepUpVerifyResponse)
def mfa_verify(
    payload: StepUpVerifyRequest,
    auth_context: FinanceAuthContext = Depends(require_finance_auth),
) -> StepUpVerifyResponse:
    if settings.auth_provider.lower() == "auth0" and not settings.finance_demo_auth:
        raise HTTPException(
            status_code=501,
            detail="Use Auth0 MFA challenge/verify flow. This endpoint is only for demo mode.",
        )
    verified_at, expires_at = verify_step_up_challenge(
        user_id=auth_context.user_id,
        challenge_id=payload.challenge_id,
        otp_code=payload.otp_code,
    )
    return StepUpVerifyResponse(mfa_verified_at=verified_at, expires_at=expires_at)


@router.post("/plaid/link-token/create", response_model=PlaidLinkTokenResponse)
def plaid_link_token_create(
    payload: PlaidLinkTokenRequest,
    auth_context: FinanceAuthContext = Depends(require_finance_auth),
    x_mfa_verified_at: str | None = Header(default=None, alias="X-Mfa-Verified-At"),
) -> PlaidLinkTokenResponse:
    require_recent_mfa(auth_context=auth_context, x_mfa_verified_at=x_mfa_verified_at)
    token = create_link_token(user_id=auth_context.user_id, payload=payload)
    audit_event("plaid_link_token_created", auth_context.user_id, {"request_id": token.request_id})
    return token


@router.post("/plaid/public-token/exchange", response_model=PlaidPublicTokenExchangeResponse)
def plaid_public_token_exchange(
    payload: PlaidPublicTokenExchangeRequest,
    auth_context: FinanceAuthContext = Depends(require_finance_auth),
    x_mfa_verified_at: str | None = Header(default=None, alias="X-Mfa-Verified-At"),
) -> PlaidPublicTokenExchangeResponse:
    require_recent_mfa(auth_context=auth_context, x_mfa_verified_at=x_mfa_verified_at)
    item_id, request_id = exchange_public_token(user_id=auth_context.user_id, public_token=payload.public_token)
    metadata = payload.metadata if isinstance(payload.metadata, dict) else {}
    institution_name = metadata.get("institution", {}).get("name")
    accounts = metadata.get("accounts", [])
    account_count = len(accounts) if isinstance(accounts, list) else 0
    audit_event(
        "plaid_public_token_exchanged",
        auth_context.user_id,
        {
            "item_id": item_id,
            "request_id": request_id,
            "institution_name": str(institution_name or ""),
            "account_count": str(account_count),
        },
    )
    return PlaidPublicTokenExchangeResponse(
        linked=True,
        item_id=item_id,
        request_id=request_id,
        institution_name=institution_name,
        account_count=account_count,
    )


def _event_id_from_payload(source: str, payload: dict, raw_body: bytes) -> str:
    for key in ("event_id", "eventId", "webhook_id", "webhookId", "request_id"):
        value = str(payload.get(key, "")).strip()
        if value:
            return value
    digest = hashlib.sha256(raw_body).hexdigest()[:24]
    return f"{source}-{digest}"


def _handle_plaid_item_states(payload: dict) -> None:
    webhook_code = str(payload.get("webhook_code", "")).strip().upper()
    item_id = str(payload.get("item_id", "")).strip()
    if webhook_code == "ITEM_LOGIN_REQUIRED":
        audit_event("plaid_item_login_required", "system", {"item_id": item_id})
    elif webhook_code == "PENDING_DISCONNECT":
        audit_event("plaid_item_pending_disconnect", "system", {"item_id": item_id})
    elif webhook_code == "PENDING_EXPIRATION":
        audit_event("plaid_item_pending_expiration", "system", {"item_id": item_id})


@router.post("/plaid/item/disconnect", response_model=PlaidDisconnectResponse)
def plaid_disconnect_item(
    payload: PlaidDisconnectRequest,
    auth_context: FinanceAuthContext = Depends(require_finance_auth),
    x_mfa_verified_at: str | None = Header(default=None, alias="X-Mfa-Verified-At"),
) -> PlaidDisconnectResponse:
    require_recent_mfa(auth_context=auth_context, x_mfa_verified_at=x_mfa_verified_at)
    request_id = remove_item(access_token=payload.access_token)
    audit_event(
        "plaid_item_removed",
        auth_context.user_id,
        {"request_id": request_id, "source_account_id": payload.source_account_id or ""},
    )
    audit_event(
        "purge_workflow_queued",
        auth_context.user_id,
        {"source": "plaid", "source_account_id": payload.source_account_id or ""},
    )
    return PlaidDisconnectResponse(removed=True, request_id=request_id, purge_queued=True)


@router.post("/webhooks/plaid", response_model=WebhookAckResponse)
async def plaid_webhook(request: Request) -> WebhookAckResponse:
    raw_body = await request.body()
    payload = parse_json_body(raw_body)
    event_id = _event_id_from_payload("plaid", payload, raw_body)

    replayed = dedupe_event("plaid", event_id)
    redacted = redact_payload(payload)
    event_type = f"{payload.get('webhook_type', 'UNKNOWN')}:{payload.get('webhook_code', 'UNKNOWN')}"
    audit_event(
        "plaid_webhook_received",
        "system",
        {
            "event_id": event_id,
            "event_type": event_type,
            "replayed": str(replayed).lower(),
            "payload_redacted": json.dumps(redacted, sort_keys=True),
        },
    )
    _handle_plaid_item_states(payload)
    return WebhookAckResponse(accepted=True, replayed=replayed, event_id=event_id, source="plaid")


@router.post("/webhooks/square", response_model=WebhookAckResponse)
async def square_webhook(
    request: Request,
    x_square_hmacsha256_signature: str | None = Header(default=None, alias="x-square-hmacsha256-signature"),
) -> WebhookAckResponse:
    raw_body = await request.body()
    if not x_square_hmacsha256_signature or not verify_square_signature(
        raw_body=raw_body.decode("utf-8"),
        header_signature=x_square_hmacsha256_signature,
    ):
        audit_event("square_webhook_invalid_signature", "system", {})
        raise HTTPException(status_code=401, detail="invalid_square_signature")

    payload = parse_json_body(raw_body)
    event_id = _event_id_from_payload("square", payload, raw_body)
    replayed = dedupe_event("square", event_id)
    redacted = redact_payload(payload)
    event_type = str(payload.get("type", payload.get("event_type", "UNKNOWN")))
    audit_event(
        "square_webhook_received",
        "system",
        {
            "event_id": event_id,
            "event_type": event_type,
            "replayed": str(replayed).lower(),
            "payload_redacted": json.dumps(redacted, sort_keys=True),
        },
    )
    return WebhookAckResponse(accepted=True, replayed=replayed, event_id=event_id, source="square")
