"""Pydantic models for artist profile and public EPK config."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EpkConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tagline: str = ""
    bio: str = ""
    booking_email: str = ""
    social: dict[str, str] = Field(default_factory=dict)
    sections: dict[str, bool] = Field(
        default_factory=lambda: {"music": True, "photos": True, "bio": True}
    )


def coerce_epk_config(raw: dict[str, Any] | None) -> EpkConfig:
    """Build EpkConfig from DB JSON — tolerate loose types so we never 500 on read."""
    if not raw:
        return EpkConfig()
    data = dict(raw)

    for key in ("tagline", "bio", "booking_email"):
        val = data.get(key)
        data[key] = "" if val is None else str(val)

    social = data.get("social") or {}
    if isinstance(social, dict):
        data["social"] = {
            str(k): ("" if v is None else str(v)) for k, v in social.items()
        }
    else:
        data["social"] = {}

    sections = data.get("sections") or {}
    if isinstance(sections, dict):

        def _to_bool(v: Any) -> bool:
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.lower() in ("true", "1", "yes", "on")
            return bool(v)

        data["sections"] = {str(k): _to_bool(v) for k, v in sections.items()}
    else:
        data["sections"] = {"music": True, "photos": True, "bio": True}

    return EpkConfig.model_validate(data)


class ArtistProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_slug: str
    display_name: str
    epk_config: EpkConfig
    profile_published: bool = False
    epk_public_published: bool = False
    homebase_published: bool = False
    epk_public: dict[str, Any] = Field(default_factory=dict)


class ArtistProfilePatch(BaseModel):
    display_name: str | None = None
    tenant_slug: str | None = None
    epk_config: EpkConfig | None = None


class PublicProfileMediaOut(BaseModel):
    asset_id: str
    title: str | None = None
    url: str | None = None
    stream_url: str | None = None
    mime_type: str | None = None


class PublicProfileOut(BaseModel):
    tenant_slug: str
    display_name: str
    tagline: str = ""
    bio: str = ""
    booking_email: str = ""
    social: dict[str, str] = Field(default_factory=dict)
    sections: dict[str, bool] = Field(default_factory=dict)
    profile_published: bool = False
    profile_published_at: str | None = None
    mood: str = ""
    format: str = "layout"
    design: dict[str, Any] = Field(default_factory=dict)
    site: dict[str, Any] = Field(default_factory=dict)
    tracks: list[PublicProfileMediaOut] = Field(default_factory=list)
    photos: list[PublicProfileMediaOut] = Field(default_factory=list)
    html: str | None = None
    css: str | None = None
    asset_bindings: dict[str, str] = Field(default_factory=dict)
    font_palette: dict[str, Any] | None = None
    google_fonts_href: str | None = None
    page_url: str | None = None


class EpkSiteOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tenant_slug: str
    display_name: str
    tagline: str = ""
    bio: str = ""
    booking_email: str = ""
    social: dict[str, str] = Field(default_factory=dict)
    sections: dict[str, bool] = Field(default_factory=dict)


class ManagerChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class ManagerChatResponse(BaseModel):
    reply: str
