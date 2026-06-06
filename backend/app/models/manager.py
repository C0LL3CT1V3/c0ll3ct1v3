"""Manager chat threads and EPK iteration training records."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.sql import func

from ..database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ManagerThread(Base):
    __tablename__ = "manager_threads"

    id = Column(String(36), primary_key=True, default=_uuid)
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = Column(String(32), nullable=False, default="general")  # general | epk_builder
    vision_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ManagerMessage(Base):
    __tablename__ = "manager_messages"

    id = Column(String(36), primary_key=True, default=_uuid)
    thread_id = Column(String(36), ForeignKey("manager_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    metadata_json = Column(SAJSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EpkIteration(Base):
    __tablename__ = "epk_iterations"

    id = Column(String(36), primary_key=True, default=_uuid)
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(String(36), ForeignKey("manager_threads.id", ondelete="SET NULL"), nullable=True, index=True)
    step = Column(String(16), nullable=False)  # generate | refine
    user_prompt = Column(Text, nullable=False, default="")
    context_snapshot = Column(SAJSON, nullable=False, default=dict)
    model_reasoning = Column(Text, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    design_patch = Column(SAJSON, nullable=False, default=dict)
    design_after = Column(SAJSON, nullable=False, default=dict)
    screenshot_storage_key = Column(String(1024), nullable=True)
    annotations_raw = Column(SAJSON, nullable=True)
    annotations_resolved = Column(SAJSON, nullable=True)
    parent_iteration_id = Column(String(36), ForeignKey("epk_iterations.id", ondelete="SET NULL"), nullable=True)
    artist_accepted = Column(Boolean, nullable=False, default=False)
    consent_for_training = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
