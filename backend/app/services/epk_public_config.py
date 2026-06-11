"""Shared helpers for booker EPK public config (avoids circular imports)."""

from __future__ import annotations

from typing import Any

from ..models.artist import Artist
from ..schemas.epk_public_schemas import EpkPublicConfig


def get_epk_public_raw(artist: Artist) -> dict[str, Any]:
    cfg = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    raw = cfg.get("epk_public")
    return raw if isinstance(raw, dict) else {}


def coerce_epk_public(raw: dict[str, Any] | None) -> EpkPublicConfig:
    if not raw:
        return EpkPublicConfig()
    data = dict(raw)
    if not (data.get("hero_video") and isinstance(data["hero_video"], dict)):
        data["hero_video"] = data.get("hero_video") or {}
    if data.get("photos") is None:
        data["photos"] = []
    if data.get("audio_samples") is None:
        data["audio_samples"] = []
    if data.get("social") is None:
        data["social"] = {}
    return EpkPublicConfig.model_validate(data)
