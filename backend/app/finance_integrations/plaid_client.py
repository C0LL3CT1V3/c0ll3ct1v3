"""Plaid link token helper with stub and API modes."""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from uuid import uuid4

from fastapi import HTTPException

from ..config import settings
from .finance_models import PlaidLinkTokenRequest, PlaidLinkTokenResponse

_token_store: dict[str, dict[str, str]] = {}


def _plaid_host() -> str:
    if settings.plaid_env == "production":
        return "https://production.plaid.com"
    if settings.plaid_env == "development":
        return "https://development.plaid.com"
    return "https://sandbox.plaid.com"


def _create_stub_link_token() -> PlaidLinkTokenResponse:
    now = int(time.time())
    return PlaidLinkTokenResponse(
        link_token=f"link-stub-{uuid4().hex}",
        expiration=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + 1800)),
        request_id=f"stub-{uuid4().hex[:12]}",
    )


def create_link_token(user_id: str, payload: PlaidLinkTokenRequest) -> PlaidLinkTokenResponse:
    if settings.plaid_link_mode == "stub":
        return _create_stub_link_token()

    if not settings.plaid_client_id or not settings.plaid_secret:
        raise HTTPException(status_code=500, detail="Plaid credentials missing.")

    body = {
        "client_id": settings.plaid_client_id,
        "secret": settings.plaid_secret,
        "client_name": payload.client_name,
        "language": payload.language,
        "country_codes": [country.strip() for country in settings.plaid_country_codes.split(",") if country.strip()],
        "products": [product.strip() for product in settings.plaid_products.split(",") if product.strip()],
        "user": {"client_user_id": user_id},
    }
    if settings.plaid_webhook_url:
        body["webhook"] = settings.plaid_webhook_url
    if payload.redirect_uri:
        body["redirect_uri"] = payload.redirect_uri

    request_data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url=f"{_plaid_host()}/link/token/create",
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Plaid request failed: {exc}") from exc

    parsed = json.loads(raw)
    try:
        return PlaidLinkTokenResponse(
            link_token=parsed["link_token"],
            expiration=parsed["expiration"],
            request_id=parsed["request_id"],
        )
    except KeyError as exc:
        raise HTTPException(status_code=502, detail="Unexpected Plaid response format.") from exc


def remove_item(access_token: str) -> str:
    """Revoke a Plaid Item and return request_id."""
    if not settings.plaid_client_id or not settings.plaid_secret:
        raise HTTPException(status_code=500, detail="Plaid credentials missing.")

    body = {
        "client_id": settings.plaid_client_id,
        "secret": settings.plaid_secret,
        "access_token": access_token,
    }
    request = urllib.request.Request(
        url=f"{_plaid_host()}/item/remove",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            details = exc.read().decode("utf-8")
        except Exception:
            details = str(exc)
        raise HTTPException(status_code=502, detail=f"Plaid item/remove failed: {details}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Plaid item/remove failed: {exc}") from exc

    parsed = json.loads(raw)
    request_id = str(parsed.get("request_id", "")).strip()
    if not request_id:
        raise HTTPException(status_code=502, detail="Unexpected Plaid item/remove response format.")
    return request_id


def exchange_public_token(user_id: str, public_token: str) -> tuple[str, str]:
    """
    Exchange Plaid public_token for access_token/item_id.

    Returns (item_id, request_id). Access token is stored server-side only.
    """
    if settings.plaid_link_mode == "stub":
        item_id = f"item-stub-{uuid4().hex[:12]}"
        request_id = f"stub-{uuid4().hex[:12]}"
        _token_store[item_id] = {"user_id": user_id, "access_token": f"access-stub-{uuid4().hex}"}
        return item_id, request_id

    if not settings.plaid_client_id or not settings.plaid_secret:
        raise HTTPException(status_code=500, detail="Plaid credentials missing.")

    body = {
        "client_id": settings.plaid_client_id,
        "secret": settings.plaid_secret,
        "public_token": public_token,
    }
    request = urllib.request.Request(
        url=f"{_plaid_host()}/item/public_token/exchange",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            details = exc.read().decode("utf-8")
        except Exception:
            details = str(exc)
        raise HTTPException(status_code=502, detail=f"Plaid token exchange failed: {details}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Plaid token exchange failed: {exc}") from exc

    parsed = json.loads(raw)
    access_token = str(parsed.get("access_token", "")).strip()
    item_id = str(parsed.get("item_id", "")).strip()
    request_id = str(parsed.get("request_id", "")).strip()
    if not access_token or not item_id or not request_id:
        raise HTTPException(status_code=502, detail="Unexpected Plaid token exchange response format.")

    # Replace this in-memory storage with encrypted DB/KMS-backed storage in production.
    _token_store[item_id] = {"user_id": user_id, "access_token": access_token}
    return item_id, request_id

