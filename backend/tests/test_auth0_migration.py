from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.auth import _provision_or_bind_user
from app.models.user import User
from app.database import Base
from app.utils.security import AuthContext, enforce_recent_mfa


def make_db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session_local()


def test_provision_user_binds_existing_email():
    db = make_db_session()
    existing = User(
        name="Legacy User",
        email="legacy@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    db.add(existing)
    db.commit()

    ctx = AuthContext(
        sub="auth0|abc123",
        email="legacy@example.com",
        name="Updated Name",
        email_verified=True,
        claims={"sub": "auth0|abc123"},
        mfa_verified_at=int(datetime.now(timezone.utc).timestamp()),
    )
    user = _provision_or_bind_user(db, ctx)
    assert user.auth0_sub == "auth0|abc123"
    assert user.email_verified is True
    assert user.name == "Updated Name"


def test_enforce_recent_mfa_accepts_fresh_claim():
    now = int(datetime.now(timezone.utc).timestamp())
    ctx = AuthContext(
        sub="auth0|fresh",
        email="fresh@example.com",
        name="Fresh User",
        email_verified=True,
        claims={"sub": "auth0|fresh"},
        mfa_verified_at=now,
    )
    enforce_recent_mfa(ctx)


def test_enforce_recent_mfa_rejects_missing_claim():
    ctx = AuthContext(
        sub="auth0|nomfa",
        email="nomfa@example.com",
        name="No MFA",
        email_verified=True,
        claims={"sub": "auth0|nomfa"},
        mfa_verified_at=None,
    )
    try:
        enforce_recent_mfa(ctx)
    except PermissionError as exc:
        assert str(exc) == "mfa_required"
        return
    raise AssertionError("Expected PermissionError for missing MFA claim")

