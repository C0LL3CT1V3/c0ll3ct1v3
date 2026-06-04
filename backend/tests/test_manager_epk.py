"""Tests for EPK draft, patch, and component registry."""

from app.services.epk_component_registry import get_component_map, resolve_annotations
from app.services.epk_draft import default_epk_design, get_or_init_draft, init_epk_draft_from_artist
from app.services.epk_patch import apply_design_patch


def test_default_epk_design_has_block_ids():
    design = default_epk_design("Test Artist")
    ids = [b["id"] for b in design["layout"]]
    assert "hero" in ids
    assert "bio-main" in ids


def test_apply_design_patch_merges_hero():
    draft = default_epk_design()
    patched = apply_design_patch(
        draft,
        {"layout": [{"id": "hero", "headline": "New Headline"}]},
    )
    hero = next(b for b in patched["layout"] if b["id"] == "hero")
    assert hero["headline"] == "New Headline"


def test_resolve_annotations_maps_component():
    design = default_epk_design()
    resolved = resolve_annotations(
        design,
        [{"note": "Bigger headline", "component_ids": ["hero"], "bbox_norm": {"x": 0, "y": 0, "w": 1, "h": 0.2}}],
    )
    assert len(resolved) == 1
    assert resolved[0]["component_id"] == "hero"
    assert "headline" in resolved[0]["prop_paths"]


def test_component_map_lists_blocks():
    design = default_epk_design()
    items = get_component_map(design)
    assert any(i["component_id"] == "hero" for i in items)
    assert any(i["component_id"] == "_theme" for i in items)


class _FakeArtist:
    epk_draft = None
    epk_config = {"tagline": "Hi", "bio": "Bio"}
    display_name = "Artist"


def test_get_or_init_draft():
    draft = get_or_init_draft(_FakeArtist())
    assert draft["layout"]
