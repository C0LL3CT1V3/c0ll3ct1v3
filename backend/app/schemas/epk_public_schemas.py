"""Booker-facing EPK public config schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HeroVideoSlot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["youtube", "asset"] = "youtube"
    url: str = ""
    asset_id: str | None = None


class PhotoSlot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    asset_id: str
    caption: str = ""


class AssetRefSlot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    asset_id: str | None = None


class AudioSampleSlot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    asset_id: str
    title: str = ""


class EpkPublicConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    template: str = "booker_v1"
    published: bool = False
    published_at: str | None = None
    hero_video: HeroVideoSlot = Field(default_factory=HeroVideoSlot)
    photos: list[PhotoSlot] = Field(default_factory=list)
    bio: str = ""
    booking_email: str = ""
    social: dict[str, str] = Field(default_factory=dict)
    tech_rider: AssetRefSlot | None = None
    audio_samples: list[AudioSampleSlot] = Field(default_factory=list)


class EpkPublicPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hero_video: HeroVideoSlot | None = None
    photos: list[PhotoSlot] | None = None
    bio: str | None = None
    booking_email: str | None = None
    social: dict[str, str] | None = None
    tech_rider: AssetRefSlot | None = None
    audio_samples: list[AudioSampleSlot] | None = None


class ResolvedMediaOut(BaseModel):
    asset_id: str
    title: str = ""
    asset_type: str = ""
    url: str | None = None
    preview_url: str | None = None


class EpkPublicOut(BaseModel):
    config: EpkPublicConfig
    resolved: dict[str, Any] = Field(default_factory=dict)
    completeness: dict[str, Any] | None = None
    preview_url: str | None = None


class PublicBookerEpkOut(BaseModel):
    tenant_slug: str
    display_name: str
    template: str = "booker_v1"
    published: bool = False
    bio: str = ""
    booking_email: str = ""
    social: dict[str, str] = Field(default_factory=dict)
    hero_video: dict[str, Any] | None = None
    photos: list[dict[str, Any]] = Field(default_factory=list)
    audio_samples: list[dict[str, Any]] = Field(default_factory=list)
    tech_rider: dict[str, Any] | None = None
    page_url: str | None = None
