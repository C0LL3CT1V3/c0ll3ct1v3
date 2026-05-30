"""EPK layout design spec (draft + published)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EpkTheme(BaseModel):
    model_config = ConfigDict(extra="ignore")

    accent: str = "#c4a574"
    background: str = "#faf9f6"
    font_pair: Literal["serif-sans", "sans", "mono"] = "serif-sans"


class LayoutBlockBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str


class HeroBlock(LayoutBlockBase):
    type: Literal["hero"] = "hero"
    headline: str = ""
    subhead: str = ""


class PhotoGridBlock(LayoutBlockBase):
    type: Literal["photo_grid"] = "photo_grid"
    columns: int = Field(default=2, ge=1, le=4)
    asset_ids: list[str] = Field(default_factory=list)


class MusicBlock(LayoutBlockBase):
    type: Literal["music"] = "music"
    asset_ids: list[str] = Field(default_factory=list)


class BioBlock(LayoutBlockBase):
    type: Literal["bio"] = "bio"
    body: str = ""


class ContactBlock(LayoutBlockBase):
    type: Literal["contact"] = "contact"
    email: str = ""


class EpkDesignInputsSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    brief: str = ""
    wireframe_asset_id: str | None = None
    style_asset_id: str | None = None
    audio_asset_id: str | None = None


class EpkDesignSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    template_id: Literal["editorial", "gallery", "minimal"] = "editorial"
    theme: EpkTheme = Field(default_factory=EpkTheme)
    layout: list[dict[str, Any]] = Field(default_factory=list)
    inputs_snapshot: EpkDesignInputsSnapshot = Field(default_factory=EpkDesignInputsSnapshot)


class EpkDesignGenerateBody(BaseModel):
    brief: str = ""
    template_id: Literal["editorial", "gallery", "minimal"] | None = None
    wireframe_asset_id: str | None = None
    style_asset_id: str | None = None
    audio_asset_id: str | None = None
    published_media_ids: list[str] | None = None
    polish_copy: bool = False


class EpkDesignOut(BaseModel):
    draft: EpkDesignSpec | None = None
    published: EpkDesignSpec | None = None
    design_published_at: str | None = None


class EpkSiteDesignOut(BaseModel):
    """Public site payload including optional published design."""

    tenant_slug: str
    display_name: str
    tagline: str = ""
    bio: str = ""
    booking_email: str = ""
    social: dict[str, str] = Field(default_factory=dict)
    sections: dict[str, bool] = Field(default_factory=dict)
    design: EpkDesignSpec | None = None
    design_published_at: str | None = None
    tracks: list[dict[str, Any]] = Field(default_factory=list)
    photos: list[dict[str, Any]] = Field(default_factory=list)
