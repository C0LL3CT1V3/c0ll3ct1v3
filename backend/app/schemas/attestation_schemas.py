"""Pydantic models for attestation ledger APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AttestationCreateBody(BaseModel):
    claim_type: str
    value: dict[str, Any] = Field(default_factory=dict)
    subject_asset_id: str | None = None
    source: str = "manual"


class AttestationConfirmBody(BaseModel):
    value: dict[str, Any] | None = None


class IngestBody(BaseModel):
    sources: list[str] | None = None
    csv_text: str | None = None
