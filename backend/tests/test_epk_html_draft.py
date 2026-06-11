"""Tests for html_v1 EPK draft sanitization."""

import pytest
from fastapi import HTTPException

from app.services.epk_html_draft import (
    HTML_FORMAT,
    build_render_document,
    inject_asset_bindings,
    is_html_draft,
    normalize_html_draft,
    sanitize_html_fragment,
)


def test_is_html_draft():
    assert is_html_draft({"format": HTML_FORMAT, "html": "<main></main>"})
    assert not is_html_draft({"layout": []})


def test_sanitize_strips_script():
    raw = "<main>Hi</main><script>alert(1)</script>"
    assert "<script" not in sanitize_html_fragment(raw)


def test_sanitize_rejects_huge_html():
    with pytest.raises(HTTPException):
        sanitize_html_fragment("x" * 600_000)


def test_inject_asset_bindings():
    html = "<img src='{{hero_photo}}' />"
    out = inject_asset_bindings(html, {"hero_photo": "https://example.com/a.jpg"})
    assert "https://example.com/a.jpg" in out


def test_normalize_html_draft():
    draft = normalize_html_draft(html="<main></main>", css="body{}", vision_id="v1", spec_snapshot="spec")
    assert draft["format"] == HTML_FORMAT
    assert draft["vision_id"] == "v1"


def test_build_render_document():
    doc = build_render_document(html="<main>Test</main>", css="body { margin: 0; }", title="T")
    assert "<!DOCTYPE html>" in doc
    assert "<main>Test</main>" in doc


def test_build_render_document_injects_google_fonts():
    href = "https://fonts.googleapis.com/css2?family=Inter:wght@400&display=swap"
    doc = build_render_document(
        html="<main>Test</main>",
        css="body { font-family: Inter, sans-serif; }",
        google_fonts_href=href,
    )
    assert "fonts.googleapis.com" in doc
    assert "Inter" in doc


def test_normalize_html_draft_adds_font_href():
    palette = {
        "heading": {
            "family": "Playfair Display",
            "google_fonts_family": "Playfair+Display",
            "weights": ["700"],
            "category": "serif",
            "confidence": 0.9,
        },
        "body": {
            "family": "Inter",
            "google_fonts_family": "Inter",
            "weights": ["400"],
            "category": "sans-serif",
            "confidence": 0.9,
        },
        "accent": None,
        "notes": "test",
        "source": "detected",
    }
    draft = normalize_html_draft(
        html="<main></main>",
        css="body {}",
        font_palette=palette,
    )
    assert draft.get("google_fonts_href")
    assert draft["font_palette"]["heading"]["family"] == "Playfair Display"
