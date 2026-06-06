"""HTML/CSS EPK draft format (html_v1) — sanitize and render for sim + Playwright."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from fastapi import HTTPException, status

from ..config import settings

HTML_FORMAT = "html_v1"
MAX_HTML_BYTES = 512_000
MAX_CSS_BYTES = 128_000

_UNSAFE_TAG_RE = re.compile(r"<\s*(script|iframe|object|embed|link|meta|base)\b[^>]*>.*?</\s*\1\s*>", re.I | re.S)
_UNSAFE_TAG_VOID_RE = re.compile(r"<\s*(script|iframe|object|embed|link|meta|base)\b[^>]*/?>", re.I)
_EVENT_ATTR_RE = re.compile(r"\s+on[a-z]+\s*=\s*([\"']).*?\1", re.I)
_JS_URL_RE = re.compile(r"\s(href|src|xlink:href)\s*=\s*([\"'])\s*javascript:.*?\2", re.I)


def is_html_draft(draft: dict | None) -> bool:
    return isinstance(draft, dict) and draft.get("format") == HTML_FORMAT


def draft_content_hash(draft: dict) -> str:
    payload = f"{draft.get('html','')}|{draft.get('css','')}|{draft.get('asset_bindings',{})}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def sanitize_html_fragment(raw: str) -> str:
    text = (raw or "").strip()
    if len(text.encode("utf-8")) > MAX_HTML_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="HTML exceeds maximum size.")
    text = _UNSAFE_TAG_RE.sub("", text)
    text = _UNSAFE_TAG_VOID_RE.sub("", text)
    text = _EVENT_ATTR_RE.sub("", text)
    text = _JS_URL_RE.sub("", text)
    return text


def sanitize_css(raw: str) -> str:
    text = (raw or "").strip()
    if len(text.encode("utf-8")) > MAX_CSS_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="CSS exceeds maximum size.")
    if "@import" in text.lower() or "javascript:" in text.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="CSS contains disallowed directives.")
    return text


def inject_asset_bindings(html: str, url_map: dict[str, str]) -> str:
    out = html
    for key, url in url_map.items():
        if not url:
            continue
        out = out.replace(f"{{{{{key}}}}}", url)
        out = out.replace(f"{{{{ {key} }}}}", url)
    return out


def build_render_document(*, html: str, css: str, title: str = "EPK Preview") -> str:
    safe_html = sanitize_html_fragment(html)
    safe_css = sanitize_css(css)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>{safe_css}</style>
</head>
<body>
{safe_html}
</body>
</html>"""


def normalize_html_draft(
    *,
    html: str,
    css: str,
    asset_bindings: dict[str, str] | None = None,
    vision_id: str | None = None,
    spec_snapshot: str | None = None,
) -> dict[str, Any]:
    return {
        "format": HTML_FORMAT,
        "html": sanitize_html_fragment(html),
        "css": sanitize_css(css),
        "asset_bindings": asset_bindings or {},
        "vision_id": vision_id,
        "spec_snapshot": (spec_snapshot or "")[:8000],
    }


def resolve_binding_urls(db, tenant_slug: str, bindings: dict[str, str]) -> dict[str, str]:
    from .vision_pack import _preview_url_for_asset
    from ..models.media import MediaAsset

    urls: dict[str, str] = {}
    for key, asset_id in (bindings or {}).items():
        asset = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.id == asset_id,
                MediaAsset.tenant_slug == tenant_slug,
                MediaAsset.is_deleted.is_(False),
            )
            .first()
        )
        if asset:
            url = _preview_url_for_asset(db, asset)
            if url:
                urls[key] = url
    return urls


def render_draft_html(db, artist, draft: dict) -> str:
    if not is_html_draft(draft):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Draft is not html_v1 format.")
    bindings = draft.get("asset_bindings") or {}
    url_map = resolve_binding_urls(db, artist.tenant_slug, bindings)
    html = inject_asset_bindings(draft.get("html") or "", url_map)
    css = draft.get("css") or ""
    title = artist.display_name or "EPK Preview"
    return build_render_document(html=html, css=css, title=title)
