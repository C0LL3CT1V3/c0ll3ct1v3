"""Rule-based genre scoring from extracted audio features."""

from __future__ import annotations

from typing import Any


def classify_genre(features: dict[str, Any]) -> list[tuple[str, float]]:
    bpm = features["bpm"]
    centroid = features["spectral_centroid"]
    rolloff = features["spectral_rolloff"]
    contrast = features["spectral_contrast"]
    zcr = features["zero_crossing_rate"]
    mfcc0 = features["mfcc_means"][0]
    mfcc1 = features["mfcc_means"][1]
    scores: dict[str, float] = {}

    folk_score = 0.0
    if 70 <= bpm <= 120:
        folk_score += 20
    if 1500 <= centroid <= 3000:
        folk_score += 15
    if rolloff < 6000:
        folk_score += 15
    if mfcc0 > -200 and mfcc1 < 50:
        folk_score += 10
    if zcr < 0.06:
        folk_score += 10
    scores["Folk / Americana"] = min(folk_score, 100)

    outlaw_score = folk_score * 0.7
    if 75 <= bpm <= 110:
        outlaw_score += 15
    if contrast > 15:
        outlaw_score += 10
    scores["Outlaw Country"] = min(outlaw_score, 100)

    indie_score = 0.0
    if 80 <= bpm <= 140:
        indie_score += 15
    if 2000 <= centroid <= 4000:
        indie_score += 15
    if contrast > 20:
        indie_score += 15
    if zcr > 0.04:
        indie_score += 10
    scores["Indie Rock / Alternative"] = min(indie_score, 100)

    country_score = 0.0
    if 80 <= bpm <= 130:
        country_score += 20
    if 1500 <= centroid <= 2800:
        country_score += 15
    if contrast < 25:
        country_score += 10
    scores["Country / Heartland Rock"] = min(country_score, 100)

    rock_score = 0.0
    if 90 <= bpm <= 150:
        rock_score += 15
    if centroid > 2500:
        rock_score += 15
    if contrast > 25:
        rock_score += 15
    if zcr > 0.05:
        rock_score += 15
    scores["Rock"] = min(rock_score, 100)

    ss_score = 0.0
    if 60 <= bpm <= 100:
        ss_score += 20
    if centroid < 2500:
        ss_score += 15
    if mfcc0 > -150 and mfcc1 < 50:
        ss_score += 15
    if zcr < 0.05:
        ss_score += 10
    scores["Singer-Songwriter"] = min(ss_score, 100)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def genre_search_queries(genre_label: str) -> list[str]:
    """Spotify search seeds from internal genre labels."""
    mapping = {
        "Folk / Americana": ["americana", "folk", "alt-country"],
        "Outlaw Country": ["outlaw country", "country"],
        "Indie Rock / Alternative": ["indie rock", "alternative rock"],
        "Country / Heartland Rock": ["heartland rock", "country rock"],
        "Rock": ["rock", "roots rock"],
        "Singer-Songwriter": ["singer-songwriter", "folk"],
    }
    return mapping.get(genre_label, [genre_label.split("/")[0].strip().lower()])
