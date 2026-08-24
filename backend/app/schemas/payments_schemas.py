"""Checkout and catalog schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["tip", "merch", "ticket"]
    amount_cents: int | None = None
    product_id: str | None = None
    event_id: str | None = None
    quantity: int = 1


class CheckoutOut(BaseModel):
    order_id: str
    checkout_url: str
    status: str = "pending"


class CatalogItemOut(BaseModel):
    id: str
    kind: str
    name: str
    description: str = ""
    image_asset_id: str | None = None
    price_cents: int = 0
    currency: str = "USD"
    sku: str | None = None
    active: bool = True
    event_id: str | None = None
    stock: int | None = None


class CatalogOut(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    checkout_available: bool = False
    tenant_slug: str | None = None
