"""Workbench vision groups — cluster related media assets."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Vision(Base):
    __tablename__ = "visions"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_slug = Column(String(64), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assets = relationship("MediaAsset", back_populates="vision")
