"""Playwright capture of EPK sim render URL."""

from __future__ import annotations

import logging

from ..config import settings

logger = logging.getLogger(__name__)


def capture_sim_screenshot(sim_url: str, *, width: int = 1280, height: int = 800) -> bytes | None:
    if not settings.epk_playwright_enabled:
        logger.info("EPK Playwright disabled; skipping screenshot.")
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not installed; skipping screenshot.")
        return None

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(sim_url, wait_until="networkidle", timeout=90_000)
            data = page.screenshot(full_page=True, type="png")
            browser.close()
            return data
    except Exception as exc:
        logger.warning("Playwright screenshot failed: %s", exc)
        return None
