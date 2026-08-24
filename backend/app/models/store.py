"""Store catalog and checkout orders (Square-backed)."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Product(Base):
    __tablename__ = "store_products"

    id = Column(String(36), primary_key=True, default=_uuid)
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(32), nullable=False, index=True)  # tip | merch | ticket
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=False, default="")
    image_asset_id = Column(String(36), nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="USD")
    sku = Column(String(64), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    square_catalog_id = Column(String(128), nullable=True)
    event_id = Column(String(64), nullable=True)
    stock = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    artist = relationship("Artist")
    lines = relationship("OrderLine", back_populates="product")


class StoreOrder(Base):
    __tablename__ = "store_orders"

    id = Column(String(36), primary_key=True, default=_uuid)
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(8), nullable=False, default="USD")
    buyer_email = Column(String(256), nullable=True)
    square_order_id = Column(String(128), nullable=True, index=True)
    square_payment_link_id = Column(String(128), nullable=True, index=True)
    checkout_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    artist = relationship("Artist")
    lines = relationship("OrderLine", back_populates="order", cascade="all, delete-orphan")


class OrderLine(Base):
    __tablename__ = "store_order_lines"

    id = Column(String(36), primary_key=True, default=_uuid)
    order_id = Column(String(36), ForeignKey("store_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("store_products.id", ondelete="SET NULL"), nullable=True)
    kind = Column(String(32), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_cents = Column(Integer, nullable=False)
    label = Column(String(160), nullable=False, default="")
    extra = Column("meta", SAJSON, nullable=False, default=dict)

    order = relationship("StoreOrder", back_populates="lines")
    product = relationship("Product", back_populates="lines")
