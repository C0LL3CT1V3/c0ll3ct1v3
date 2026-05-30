"""Audience map report schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenreScore(BaseModel):
    genre: str
    score: float


class AudioFeaturesOut(BaseModel):
    bpm: float
    key: str
    duration_seconds: float


class TieredArtist(BaseModel):
    name: str
    tier: str
    followers: int = 0
    popularity: int = 0
    genres: list[str] = Field(default_factory=list)
    spotify_url: str | None = None
    spotify_id: str | None = None
    source: str = "spotify"
    why: str = ""


class AudienceMapReport(BaseModel):
    primary_genre: str
    confidence: float
    subgenres: list[GenreScore] = Field(default_factory=list)
    all_genre_scores: list[GenreScore] = Field(default_factory=list)
    audio_features: AudioFeaturesOut
    pitch_line: str = ""
    tiers: dict[str, list[TieredArtist]] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    mode: str = "full"
    reference_asset_id: str | None = None
    track_title: str | None = None

    def to_epk_profile(self) -> dict[str, Any]:
        return {
            "primary_genre": self.primary_genre,
            "confidence": self.confidence,
            "pitch_line": self.pitch_line,
            "audio_features": self.audio_features.model_dump(),
            "tiers": {k: [a.model_dump() for a in v] for k, v in self.tiers.items()},
            "actions": self.actions,
            "subgenres": [s.model_dump() for s in self.subgenres],
            "notes": self.notes,
        }
