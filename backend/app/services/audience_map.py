"""Build audience map: audio features, genres, tiered similar artists, actions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..schemas.audience_schemas import (
    AudienceMapReport,
    AudioFeaturesOut,
    GenreScore,
    TieredArtist,
)
from .audio_features import extract_features
from .genre_classify import classify_genre, genre_search_queries
from .spotify_client import SpotifyClient, SpotifyError, spotify_available

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _load_yaml(name: str) -> dict[str, Any]:
    path = _CONFIG_DIR / name
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _tier_for_artist(
    artist: dict[str, Any],
    tier_cfg: dict[str, Any],
    *,
    seed_lookup: dict[str, str] | None = None,
) -> str | None:
    name_key = (artist.get("name") or "").strip().lower()
    if seed_lookup and name_key in seed_lookup:
        return seed_lookup[name_key]

    followers = artist.get("followers", 0)
    pop = artist.get("popularity", 0)
    if followers == 0 and pop == 0:
        return None
    asp = tier_cfg.get("aspiration", {})
    eng = tier_cfg.get("engagement", {})
    peer = tier_cfg.get("peer", {})

    if followers >= asp.get("min_followers", 500000) or pop >= asp.get("min_popularity", 65):
        return "aspiration"
    if (
        eng.get("min_followers", 15000) <= followers <= eng.get("max_followers", 500000)
        and eng.get("min_popularity", 35) <= pop <= eng.get("max_popularity", 65)
    ):
        return "engagement"
    if followers <= peer.get("max_followers", 100000) and pop <= peer.get("max_popularity", 45):
        return "peer"
    if followers < eng.get("min_followers", 15000):
        return "peer"
    return "engagement"


def _seed_tier_lookup(seeds_cfg: dict[str, Any]) -> dict[str, str]:
    """Map artist name (lower) -> tier from genre seed YAML."""
    lookup: dict[str, str] = {}
    by_genre = seeds_cfg.get("by_genre") or {}
    for _genre, block in by_genre.items():
        if not isinstance(block, dict):
            continue
        for tier, names in block.items():
            for name in names:
                lookup[name.strip().lower()] = tier
    return lookup


def _seed_fallback(genre: str, seeds_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    by_genre = seeds_cfg.get("by_genre") or {}
    block = by_genre.get(genre) or {}
    out: list[dict[str, Any]] = []
    for tier, names in block.items():
        for name in names:
            out.append({"name": name, "tier": tier, "source": "seed", "followers": 0, "popularity": 0, "genres": []})
    return out


def _collect_spotify_candidates(genre_scores: list[tuple[str, float]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    client = SpotifyClient()
    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    threshold = cfg.get("genre_score_threshold", 30)
    top_genres = [g for g, s in genre_scores if s >= threshold][:3]

    for genre in top_genres:
        for query in genre_search_queries(genre):
            try:
                hits = client.search_artists(query, limit=cfg.get("max_search_per_query", 5))
            except Exception:
                continue
            for artist in hits:
                if artist["spotify_id"] in seen:
                    continue
                seen.add(artist["spotify_id"])
                artist["source_genre"] = genre
                candidates.append(artist)
                try:
                    related_list = client.related_artists(artist["spotify_id"])
                except Exception:
                    related_list = []
                for related in related_list[: cfg.get("max_related_per_seed", 5)]:
                    if related["spotify_id"] in seen:
                        continue
                    seen.add(related["spotify_id"])
                    related["source_genre"] = genre
                    candidates.append(related)
    return candidates


def _tier_candidates(
    candidates: list[dict[str, Any]],
    tier_cfg: dict[str, Any],
    seeds_cfg: dict[str, Any],
    primary_genre: str,
) -> dict[str, list[TieredArtist]]:
    tiers_raw: dict[str, list[TieredArtist]] = {
        "aspiration": [],
        "engagement": [],
        "peer": [],
    }
    seen_names: set[str] = set()

    seed_lookup = _seed_tier_lookup(seeds_cfg)
    skip_names = {
        "americana",
        "outlaw country",
        "folk",
        "country",
        "rock",
        "indie",
    }
    for c in candidates:
        name = c.get("name", "").strip()
        if not name or name.lower() in seen_names or name.lower() in skip_names:
            continue
        tier_key = _tier_for_artist(c, tier_cfg, seed_lookup=seed_lookup)
        if not tier_key:
            continue
        cap = tier_cfg.get(tier_key, {}).get("max_per_tier", 8)
        if len(tiers_raw[tier_key]) >= cap:
            continue
        seen_names.add(name.lower())
        tiers_raw[tier_key].append(
            TieredArtist(
                name=name,
                tier=tier_key,
                followers=c.get("followers", 0),
                popularity=c.get("popularity", 0),
                genres=c.get("genres", []),
                spotify_url=c.get("spotify_url"),
                spotify_id=c.get("spotify_id"),
                source=c.get("source", "spotify"),
                why=f"Matched {c.get('source_genre', primary_genre)} cluster",
            )
        )

    if sum(len(v) for v in tiers_raw.values()) < 6:
        for seed in _seed_fallback(primary_genre, seeds_cfg):
            name = seed["name"]
            if name.lower() in seen_names:
                continue
            tier_key = seed["tier"]
            cap = tier_cfg.get(tier_key, {}).get("max_per_tier", 8)
            if len(tiers_raw[tier_key]) >= cap:
                continue
            seen_names.add(name.lower())
            enriched = seed
            if spotify_available():
                try:
                    client = SpotifyClient()
                    hit = client.enrich_by_name(name)
                    if hit:
                        enriched = {**seed, **hit, "source": "seed+spotify"}
                except SpotifyError:
                    pass
            tiers_raw[tier_key].append(
                TieredArtist(
                    name=name,
                    tier=tier_key,
                    followers=enriched.get("followers", 0),
                    popularity=enriched.get("popularity", 0),
                    genres=enriched.get("genres", []),
                    spotify_url=enriched.get("spotify_url"),
                    spotify_id=enriched.get("spotify_id"),
                    source=enriched.get("source", "seed"),
                    why="Curated fallback for thin API results",
                )
            )
    return tiers_raw


def _build_pitch_line(primary: str, features: dict[str, Any], subgenres: list[GenreScore]) -> str:
    subs = ", ".join(s.genre for s in subgenres[:2]) if subgenres else ""
    extra = f" with {subs} lean" if subs else ""
    return (
        f"{primary}{extra} at {features['bpm']} BPM in {features['key']} — "
        "acoustic-forward, lyric-driven material for Americana and indie audiences."
    )


def _build_actions(tiers: dict[str, list[TieredArtist]], primary: str) -> list[str]:
    actions: list[str] = []
    eng = tiers.get("engagement", [])
    asp = tiers.get("aspiration", [])
    if eng:
        names = ", ".join(a.name for a in eng[:5])
        actions.append(f"Follow and engage (comments, stories) with mid-tier comps: {names}.")
        actions.append("Study their release cadence, playlist placements, and which playlists feature them.")
    if asp:
        names = ", ".join(a.name for a in asp[:3])
        actions.append(f"Aspiration tier — study arrangement and brand positioning: {names}.")
    actions.append(f"Pitch playlists using tags: {primary}, outlaw country, americana, singer-songwriter.")
    actions.append("Post 2–3 short clips per week tagging engagement-tier artists when relevant (not spam).")
    return actions


def _build_notes(features: dict[str, Any], primary: str) -> list[str]:
    notes: list[str] = []
    if primary in ("Folk / Americana", "Outlaw Country", "Singer-Songwriter"):
        notes.append(
            f"Warm, lyric-forward profile at {features['bpm']} BPM in {features['key']}."
        )
    if features.get("spectral_contrast", 0) > 25:
        notes.append("Dynamic arrangement — lean into verse/chorus contrast in social clips.")
    if features.get("zero_crossing_rate", 0) < 0.04:
        notes.append("Mostly acoustic timbre; playthrough and live-room content fits better than EDM-style edits.")
    return notes


def build_audience_map(
    audio_path: str,
    *,
    track_title: str | None = None,
    reference_asset_id: str | None = None,
) -> AudienceMapReport:
    """Analyze a local audio file and return a full audience map report."""
    cfg = _load_yaml("audience_tiers.yaml")
    seeds_cfg = _load_yaml("genre_seed_artists.yaml")
    tier_cfg = cfg.get("tiers") or {}

    features = extract_features(audio_path)
    genre_scores = classify_genre(features)
    primary = genre_scores[0][0] if genre_scores else "Unknown"
    confidence = genre_scores[0][1] if genre_scores else 0.0

    subgenres = [
        GenreScore(genre=g, score=s)
        for g, s in genre_scores[1:4]
        if s >= cfg.get("genre_score_threshold", 30)
    ]
    all_scores = [GenreScore(genre=g, score=s) for g, s in genre_scores if s > 10]

    mode = "rules_only"
    candidates: list[dict[str, Any]] = []
    if spotify_available():
        try:
            candidates = _collect_spotify_candidates(genre_scores, cfg)
            mode = "full"
        except SpotifyError:
            mode = "seed_fallback"

    tiers = _tier_candidates(candidates, tier_cfg, seeds_cfg, primary)
    if not candidates:
        tiers = _tier_candidates([], tier_cfg, seeds_cfg, primary)
        mode = "seed_fallback"

    audio_out = AudioFeaturesOut(
        bpm=features["bpm"],
        key=features["key"],
        duration_seconds=features["duration_seconds"],
    )
    return AudienceMapReport(
        primary_genre=primary,
        confidence=confidence,
        subgenres=subgenres,
        all_genre_scores=all_scores,
        audio_features=audio_out,
        pitch_line=_build_pitch_line(primary, features, subgenres),
        tiers=tiers,
        actions=_build_actions(tiers, primary),
        notes=_build_notes(features, primary),
        mode=mode,
        reference_asset_id=reference_asset_id,
        track_title=track_title,
    )


def report_to_markdown(report: AudienceMapReport) -> str:
    lines = [
        f"# Audience map — {report.track_title or 'Track'}",
        "",
        f"**Primary genre:** {report.primary_genre} ({report.confidence:.0f}% rule score)",
        f"**Pitch line:** {report.pitch_line}",
        f"**BPM / key:** {report.audio_features.bpm} / {report.audio_features.key}",
        f"**Mode:** {report.mode}",
        "",
    ]
    for tier_key, label in [
        ("aspiration", "Established — reach goals"),
        ("engagement", "Up-and-coming — realistic engagement"),
        ("peer", "Peer league — collaborators"),
    ]:
        artists = report.tiers.get(tier_key, [])
        lines.append(f"## {label}")
        if not artists:
            lines.append("_None matched — adjust tiers or add Spotify credentials._")
        for a in artists:
            meta = f"{a.followers:,} followers, popularity {a.popularity}" if a.followers else "seed data"
            lines.append(f"- **{a.name}** ({meta}) — {a.why}")
        lines.append("")
    lines.append("## Actions")
    for act in report.actions:
        lines.append(f"- {act}")
    if report.notes:
        lines.append("")
        lines.append("## Notes")
        for n in report.notes:
            lines.append(f"- {n}")
    lines.append("")
    lines.append(f"_Generated {datetime.now(timezone.utc).isoformat()}_")
    return "\n".join(lines)


def cache_audience_profile(epk_config: dict, report: AudienceMapReport) -> dict:
    merged = dict(epk_config) if isinstance(epk_config, dict) else {}
    merged["audience_profile"] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **report.to_epk_profile(),
        "reference_asset_id": report.reference_asset_id,
        "track_title": report.track_title,
        "mode": report.mode,
        "full_report": report.model_dump(),
    }
    return merged


def audience_profile_from_cache(raw: dict) -> AudienceMapReport | None:
    full = raw.get("full_report")
    if isinstance(full, dict):
        return AudienceMapReport.model_validate(full)
    return None
