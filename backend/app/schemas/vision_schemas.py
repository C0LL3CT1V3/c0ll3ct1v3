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


class VisionPackAssetOut(BaseModel):
    id: str
    title: str | None = None
    asset_type: str
    vision_role: str
    preview_url: str | None = None


class VisionPackCountsOut(BaseModel):
    wireframe: int = 0
    references: int = 0
    media: int = 0


class VisionPackOut(BaseModel):
    vision_id: str
    vision_title: str
    wireframe: VisionPackAssetOut | None = None
    references: list[VisionPackAssetOut] = Field(default_factory=list)
    media: list[VisionPackAssetOut] = Field(default_factory=list)
    counts: VisionPackCountsOut
