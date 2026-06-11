"""Generate PDF export of published booker EPK."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from ..config import settings

logger = logging.getLogger(__name__)


def capture_epk_pdf(page_url: str, *, base_url: str | None = None) -> bytes | None:
    """Render booker EPK HTML page to PDF via Playwright."""
    if not settings.epk_playwright_enabled:
        logger.info("EPK Playwright disabled; cannot generate PDF.")
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not installed; cannot generate PDF.")
        return None

    base = (base_url or settings.epk_sim_base_url).rstrip("/")
    full_url = page_url if page_url.startswith("http") else f"{base}{page_url}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(full_url, wait_until="networkidle", timeout=90_000)
            data = page.pdf(format="A4", print_background=True)
            browser.close()
            return data
    except Exception as exc:
        logger.warning("Playwright PDF failed: %s", exc)
        return None


def generate_booker_epk_pdf(tenant_slug: str) -> bytes:
    page_path = f"/artists/public/{tenant_slug}/epk/page"
    pdf = capture_epk_pdf(page_path)
    if not pdf:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF export unavailable — enable epk_playwright_enabled and ensure Playwright is installed.",
        )
    return pdf
