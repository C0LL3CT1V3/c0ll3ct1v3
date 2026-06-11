"""Streaming platform logo links for booker EPK HTML."""

from __future__ import annotations

import html

_LOGOS: dict[str, tuple[str, str]] = {
    "spotify": ("Spotify", "https://cdn.simpleicons.org/spotify/1DB954"),
    "soundcloud": ("SoundCloud", "https://cdn.simpleicons.org/soundcloud/FF5500"),
    "bandcamp": ("Bandcamp", "https://cdn.simpleicons.org/bandcamp/408294"),
    "youtube": ("YouTube", "https://cdn.simpleicons.org/youtube/FF0000"),
}

_FALLBACK_LOGO = "https://cdn.simpleicons.org/link/FFFFFF"


def streaming_logo_link(platform: str, url: str) -> str:
    key = platform.lower()
    label, src = _LOGOS.get(key, (platform.replace("_", " ").title(), _FALLBACK_LOGO))
    safe_url = html.escape(url, quote=True)
    safe_label = html.escape(label)
    safe_src = html.escape(src, quote=True)
    return (
        f'<a class="booker-epk-streaming-logo" href="{safe_url}" '
        f'target="_blank" rel="noreferrer" aria-label="{safe_label}" title="{safe_label}">'
        f'<img src="{safe_src}" alt="{safe_label}" width="36" height="36" loading="lazy" />'
        f"</a>"
    )
