"""Catalog and Square-hosted checkout (tips now; merch/tickets later)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.artist import Artist
from ..models.store import OrderLine, Product, StoreOrder
from ..schemas.payments_schemas import CheckoutRequest
from .artist_service import resolve_artist_by_public_slug
from .square_checkout import checkout_configured, create_payment_link

TIP_AMOUNT_CENTS_MIN = 100
TIP_AMOUNT_CENTS_MAX = 1_000_000
NOT_IMPLEMENTED = "Merch and ticket checkout is not available yet."


def serialize_product(row: Product) -> dict[str, Any]:
    return {
        "id": row.id,
        "kind": row.kind,
        "name": row.name,
        "description": row.description or "",
        "image_asset_id": row.image_asset_id,
        "price_cents": row.price_cents,
        "currency": row.currency,
        "sku": row.sku,
        "active": row.active,
        "event_id": row.event_id,
        "stock": row.stock,
    }


def list_catalog(db: Session, artist: Artist, *, public: bool = False) -> list[dict[str, Any]]:
    query = db.query(Product).filter(Product.artist_id == artist.id)
    if public:
        query = query.filter(Product.active.is_(True), Product.kind.in_(("merch", "ticket")))
    rows = query.order_by(Product.kind, Product.name).all()
    return [serialize_product(row) for row in rows]


def get_public_catalog(db: Session, tenant_slug: str) -> dict[str, Any]:
    artist = resolve_artist_by_public_slug(db, tenant_slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Catalog not found.")
    return {
        "tenant_slug": artist.tenant_slug,
        "items": list_catalog(db, artist, public=True),
        "checkout_available": checkout_configured(),
    }


def get_my_catalog(db: Session, artist: Artist) -> dict[str, Any]:
    return {
        "items": list_catalog(db, artist, public=False),
        "checkout_available": checkout_configured(),
    }


def create_public_checkout(db: Session, tenant_slug: str, body: CheckoutRequest) -> dict[str, Any]:
    artist = resolve_artist_by_public_slug(db, tenant_slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artist not found.")
    return create_checkout(db, artist, body)


def create_checkout(db: Session, artist: Artist, body: CheckoutRequest) -> dict[str, Any]:
    kind = (body.kind or "").strip().lower()
    if kind in ("merch", "ticket"):
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=NOT_IMPLEMENTED)
    if kind != "tip":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="kind must be tip, merch, or ticket.")

    amount_cents = int(body.amount_cents or 0)
    if amount_cents < TIP_AMOUNT_CENTS_MIN or amount_cents > TIP_AMOUNT_CENTS_MAX:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Tip amount must be between $1 and $10,000.",
        )
    if not checkout_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Square checkout is not configured.",
        )

    quantity = max(int(body.quantity or 1), 1)
    label = f"Tip — {artist.display_name}"[:160]
    order = StoreOrder(
        artist_id=artist.id,
        status="pending",
        amount_cents=amount_cents * quantity,
        currency="USD",
    )
    db.add(order)
    db.flush()
    db.add(
        OrderLine(
            order_id=order.id,
            product_id=None,
            kind="tip",
            quantity=quantity,
            unit_cents=amount_cents,
            label=label,
            extra={"event_id": body.event_id} if body.event_id else {},
        )
    )
    db.commit()
    db.refresh(order)

    try:
        link = create_payment_link(
            idempotency_key=order.id,
            name=label,
            amount_cents=order.amount_cents,
            currency=order.currency,
        )
    except HTTPException:
        order.status = "failed"
        db.commit()
        raise

    order.square_payment_link_id = link.get("id") or None
    order.square_order_id = link.get("order_id") or None
    order.checkout_url = link.get("url")
    db.commit()
    db.refresh(order)
    return {
        "order_id": order.id,
        "checkout_url": order.checkout_url,
        "status": order.status,
    }


def mark_orders_paid_from_square_event(db: Session, payload: dict[str, Any]) -> int:
    """Mark matching pending orders paid. Returns how many rows updated."""
    event_type = str(payload.get("type") or payload.get("event_type") or "").lower()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    obj = data.get("object") if isinstance(data.get("object"), dict) else data

    square_order_ids: list[str] = []
    payment = obj.get("payment") if isinstance(obj.get("payment"), dict) else None
    order = obj.get("order") if isinstance(obj.get("order"), dict) else None

    if payment:
        pay_status = str(payment.get("status") or "").upper()
        if pay_status in ("COMPLETED", "APPROVED"):
            oid = str(payment.get("order_id") or "").strip()
            if oid:
                square_order_ids.append(oid)
    if order:
        state = str(order.get("state") or order.get("status") or "").upper()
        if state in ("COMPLETED", "PAID"):
            oid = str(order.get("id") or "").strip()
            if oid:
                square_order_ids.append(oid)

    if "payment" in event_type or "order" in event_type:
        # Some payloads put ids on the object itself.
        oid = str(obj.get("order_id") or "").strip()
        if oid:
            square_order_ids.append(oid)

    updated = 0
    seen: set[str] = set()
    for oid in square_order_ids:
        if not oid or oid in seen:
            continue
        seen.add(oid)
        row = (
            db.query(StoreOrder)
            .filter(StoreOrder.square_order_id == oid, StoreOrder.status == "pending")
            .first()
        )
        if not row:
            continue
        row.status = "paid"
        updated += 1
    if updated:
        db.commit()
    return updated
