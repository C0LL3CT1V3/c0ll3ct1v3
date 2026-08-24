"""Thin Square Checkout (Payment Links) client. No PAN on our origin."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from ..config import settings

SQUARE_VERSION = "2024-12-18"


def checkout_configured() -> bool:
    return bool(settings.square_access_token.strip() and settings.square_location_id.strip())


def create_payment_link(
    *,
    idempotency_key: str,
    name: str,
    amount_cents: int,
    currency: str = "USD",
) -> dict[str, Any]:
    if not checkout_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Square checkout is not configured.",
        )
    base = settings.square_base_url.rstrip("/")
    url = f"{base}/online-checkout/payment-links"
    payload = {
        "idempotency_key": idempotency_key,
        "quick_pay": {
            "name": (name or "Payment")[:50],
            "price_money": {"amount": int(amount_cents), "currency": currency or "USD"},
            "location_id": settings.square_location_id.strip(),
        },
    }
    headers = {
        "Authorization": f"Bearer {settings.square_access_token.strip()}",
        "Content-Type": "application/json",
        "Square-Version": SQUARE_VERSION,
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Square checkout unavailable.",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Square checkout unavailable.",
        )

    data = response.json() if response.content else {}
    link = data.get("payment_link") if isinstance(data, dict) else None
    if not isinstance(link, dict) or not link.get("url"):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Square checkout unavailable.",
        )
    order_id = link.get("order_id")
    if not order_id and isinstance(link.get("order"), dict):
        order_id = link["order"].get("id")
    return {
        "id": str(link.get("id") or ""),
        "url": str(link["url"]),
        "order_id": str(order_id or "") or None,
    }
