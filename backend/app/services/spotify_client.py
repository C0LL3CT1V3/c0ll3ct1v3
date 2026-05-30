"""Spotify Web API — Client Credentials flow for audience mapping."""

from __future__ import annotations

import time
from typing import Any

import httpx

from ..config import settings

_TOKEN: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


class SpotifyError(RuntimeError):
    pass


class SpotifyClient:
    def __init__(self) -> None:
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            raise SpotifyError("Spotify credentials not configured (SPOTIFY_CLIENT_ID/SECRET).")

    def _token(self) -> str:
        now = time.time()
        if _TOKEN["access_token"] and _TOKEN["expires_at"] > now + 30:
            return _TOKEN["access_token"]
        resp = httpx.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        _TOKEN["access_token"] = data["access_token"]
        _TOKEN["expires_at"] = now + int(data.get("expires_in", 3600))
        return _TOKEN["access_token"]

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"https://api.spotify.com/v1{path}"
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {self._token()}"},
            params=params or {},
            timeout=30.0,
        )
        if resp.status_code == 429:
            raise SpotifyError("Spotify rate limit exceeded.")
        resp.raise_for_status()
        return resp.json()

    def get_artists_batch(self, artist_ids: list[str]) -> list[dict[str, Any]]:
        if not artist_ids:
            return []
        out: list[dict[str, Any]] = []
        for aid in artist_ids[:50]:
            try:
                out.append(self.get_artist(aid))
            except SpotifyError:
                continue
        return out

    def search_artists(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        data = self._get("/search", params={"q": query, "type": "artist", "limit": limit})
        items = data.get("artists", {}).get("items", [])
        ids = [a["id"] for a in items if a.get("id")]
        if not ids:
            return []
        return self.get_artists_batch(ids)

    def get_artist(self, artist_id: str) -> dict[str, Any]:
        return _normalize_artist(self._get(f"/artists/{artist_id}"))

    def related_artists(self, artist_id: str) -> list[dict[str, Any]]:
        data = self._get(f"/artists/{artist_id}/related-artists")
        return [_normalize_artist(a) for a in data.get("artists", []) if a.get("id")]

    def enrich_by_name(self, name: str) -> dict[str, Any] | None:
        hits = self.search_artists(name, limit=1)
        return hits[0] if hits else None


def _normalize_artist(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "spotify_id": raw.get("id"),
        "name": raw.get("name") or "",
        "followers": int((raw.get("followers") or {}).get("total") or 0),
        "popularity": int(raw.get("popularity") or 0),
        "genres": list(raw.get("genres") or []),
        "spotify_url": (raw.get("external_urls") or {}).get("spotify"),
    }


def spotify_available() -> bool:
    return bool(settings.spotify_client_id and settings.spotify_client_secret and settings.audience_analysis_enabled)
