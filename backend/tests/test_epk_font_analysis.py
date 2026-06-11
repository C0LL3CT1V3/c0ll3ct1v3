"""Tests for EPK font detection and Google Fonts helpers."""

from unittest.mock import patch

from app.services.epk_font_analysis import (
    build_google_fonts_href,
    detect_fonts_from_vision_pack,
    normalize_font_palette,
    sanitize_google_fonts_href,
    stub_font_palette,
)


def test_build_google_fonts_href():
    palette = stub_font_palette()
    href = build_google_fonts_href(palette)
    assert href
    assert href.startswith("https://fonts.googleapis.com/css2?")
    assert "Playfair+Display" in href
    assert "Inter" in href


def test_sanitize_google_fonts_href_rejects_bad_urls():
    assert sanitize_google_fonts_href("https://evil.example/css2?family=Inter") is None
    assert sanitize_google_fonts_href("javascript:alert(1)") is None
    good = build_google_fonts_href(stub_font_palette())
    assert sanitize_google_fonts_href(good) == good


def test_normalize_font_palette_fallback():
    out = normalize_font_palette({"heading": {"family": "Oswald", "weights": ["700"]}})
    assert out["heading"]["family"] == "Oswald"
    assert out["body"]["family"]


def test_detect_fonts_stub_without_references():
    pack = {"vision_id": "v1", "references": [], "wireframe": None}
    out = detect_fonts_from_vision_pack(pack)
    assert out["heading"]["family"]
    assert out["source"] == "stub"


@patch("app.services.manager_llm._call_llm_json_any")
@patch("app.services.manager_llm.manager_llm_configured", return_value=True)
@patch("app.services.epk_font_analysis.settings")
def test_detect_fonts_from_references(mock_settings, _configured, mock_llm):
    mock_settings.openrouter_api_key = "test-key"
    mock_settings.manager_vision_model = "google/gemini-2.0-flash-001"
    mock_llm.return_value = {
        "heading": {
            "family": "Bebas Neue",
            "google_fonts_family": "Bebas+Neue",
            "weights": ["400"],
            "category": "sans-serif",
            "confidence": 0.9,
        },
        "body": {
            "family": "Lora",
            "google_fonts_family": "Lora",
            "weights": ["400", "600"],
            "category": "serif",
            "confidence": 0.85,
        },
        "accent": None,
        "notes": "Bold condensed headlines with literary body.",
    }
    pack = {
        "references": [{"preview_url": "https://example.com/ref1.jpg"}],
        "wireframe": None,
    }
    out = detect_fonts_from_vision_pack(pack)
    assert out["heading"]["family"] == "Bebas Neue"
    assert out["body"]["family"] == "Lora"
    assert mock_llm.called
