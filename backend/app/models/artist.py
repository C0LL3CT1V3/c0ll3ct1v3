"""Artist profile linked to Auth0 identity and public EPK tenant slug."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.sql import func

from ..database import Base


def default_epk_config() -> dict:
    return {
        "tagline": "",
        "bio": "",
        "booking_email": "",
        "social": {},
        "sections": {"music": True, "photos": True, "bio": True},
    }


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    auth0_sub = Column(String, unique=True, nullable=False, index=True)
    tenant_slug = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    epk_config = Column(SAJSON, nullable=False, default=default_epk_config)
    manager_system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
