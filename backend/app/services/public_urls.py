"""Browser-facing public site URLs (artist subdomains)."""

from __future__ import annotations

from ..config import settings


def public_site_origin(tenant_slug: str) -> str:
    domain = (settings.public_site_domain or "c0ll3ct1v3.xyz").strip()
    return f"https://{tenant_slug}.{domain}"


def public_epk_url(tenant_slug: str) -> str:
    return f"{public_site_origin(tenant_slug)}/epk"


def public_homebase_url(tenant_slug: str) -> str:
    return f"{public_site_origin(tenant_slug)}/homebase"
