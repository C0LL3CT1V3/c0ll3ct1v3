"""Infer creative media asset_type from filename and MIME type."""

from __future__ import annotations

from pathlib import Path

_EXTENSION_TYPES: dict[str, str] = {
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
    ".avif": "image",
    ".heic": "image",
    ".heif": "image",
    ".bmp": "image",
    ".tif": "image",
    ".tiff": "image",
    ".svg": "image",
    ".mp3": "audio",
    ".wav": "audio",
    ".flac": "audio",
    ".aac": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".opus": "audio",
    ".wma": "audio",
    ".mp4": "video",
    ".mov": "video",
    ".webm": "video",
    ".mkv": "video",
    ".m4v": "video",
    ".zip": "archive",
}

_MIME_PREFIX_TYPES: tuple[tuple[str, str], ...] = (
    ("image/", "image"),
    ("audio/", "audio"),
    ("video/", "video"),
)


def infer_asset_type(filename: str, mime_type: str, client_hint: str | None = None) -> str:
    """Resolve asset_type; prefer extension, then MIME. Corrects wrong client hints."""
    ext = Path(filename).suffix.lower()
    from_ext = _EXTENSION_TYPES.get(ext)
    mime = (mime_type or "").strip().lower()

    from_mime = None
    for prefix, kind in _MIME_PREFIX_TYPES:
        if mime.startswith(prefix):
            from_mime = kind
            break
    if mime in ("application/zip", "application/x-zip-compressed"):
        from_mime = "archive"

    if from_ext:
        if client_hint and client_hint != from_ext and client_hint in {"audio", "image", "video", "document", "archive"}:
            return from_ext
        return from_ext

    if from_mime:
        return from_mime

    if client_hint in {"audio", "image", "video", "document", "archive"}:
        return client_hint

    return "document"


def infer_mime_type(filename: str, mime_type: str) -> str:
    ext = Path(filename).suffix.lower()
    if mime_type and mime_type != "application/octet-stream":
        return mime_type
    fallback = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".zip": "application/zip",
    }
    return fallback.get(ext, mime_type or "application/octet-stream")
