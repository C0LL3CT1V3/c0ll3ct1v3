"""Pydantic models for workbench vision groups."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .media_schemas import AssetListItem


class VisionCreateBody(BaseModel):
    title: str = Field(default="Untitled vision", min_length=1, max_length=512)


class VisionUpdateBody(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=512)
    sort_order: int | None = None


class VisionOut(BaseModel):
    id: str
    tenant_slug: str
    title: str
    sort_order: int
    created_at: Any

    model_config = {"from_attributes": True}


class WorkbenchOut(BaseModel):
    visions: list[VisionOut]
    assets: list[AssetListItem]
