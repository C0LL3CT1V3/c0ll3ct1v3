"""Tests for Square checkout rails."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.account import BankAccount  # noqa: F401
from app.models.artist import Artist
from app.models.media import MediaAsset  # noqa: F401
from app.models.store import StoreOrder  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.vision import Vision  # noqa: F401
from app.schemas.payments_schemas import CheckoutRequest
from app.services.payments import (
    NOT_IMPLEMENTED,
    create_checkout,
    get_my_catalog,
    get_public_catalog,
    mark_orders_paid_from_square_event,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        auth0_sub="auth0|pay",
        tenant_slug="payartist",
        display_name="Pay Artist",
        epk_config={},
    )
    session.add(artist)
    session.commit()
    yield session, artist
    session.close()


def test_catalog_empty(db):
    session, artist = db
    mine = get_my_catalog(session, artist)
    assert mine["items"] == []
    public = get_public_catalog(session, artist.tenant_slug)
    assert public["items"] == []
    assert public["tenant_slug"] == "payartist"


def test_merch_and_ticket_checkout_are_501(db):
    session, artist = db
    with pytest.raises(HTTPException) as merch:
        create_checkout(session, artist, CheckoutRequest(kind="merch", product_id="x"))
    assert merch.value.status_code == 501
    assert merch.value.detail == NOT_IMPLEMENTED

    with pytest.raises(HTTPException) as ticket:
        create_checkout(session, artist, CheckoutRequest(kind="ticket", event_id="ev1"))
    assert ticket.value.status_code == 501


def test_tip_checkout_creates_order_with_mocked_square(db):
    session, artist = db
    with patch("app.services.payments.checkout_configured", return_value=True), patch(
        "app.services.payments.create_payment_link",
        return_value={
            "id": "plink_1",
            "url": "https://square.link/u/test",
            "order_id": "sq_order_1",
        },
    ):
        out = create_checkout(session, artist, CheckoutRequest(kind="tip", amount_cents=1000))
    assert out["checkout_url"] == "https://square.link/u/test"
    assert out["status"] == "pending"
    row = session.query(StoreOrder).filter(StoreOrder.id == out["order_id"]).one()
    assert row.amount_cents == 1000
    assert row.square_order_id == "sq_order_1"
    assert row.lines[0].kind == "tip"


def test_webhook_marks_order_paid(db):
    session, artist = db
    order = StoreOrder(
        artist_id=artist.id,
        status="pending",
        amount_cents=500,
        currency="USD",
        square_order_id="sq_order_paid",
    )
    session.add(order)
    session.commit()
    updated = mark_orders_paid_from_square_event(
        session,
        {
            "type": "payment.updated",
            "data": {"object": {"payment": {"status": "COMPLETED", "order_id": "sq_order_paid"}}},
        },
    )
    assert updated == 1
    session.refresh(order)
    assert order.status == "paid"
