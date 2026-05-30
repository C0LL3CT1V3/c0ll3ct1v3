"""Artist profile provisioning and tenant slug helpers."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from ..config import settings
from ..models.artist import Artist, default_epk_config
from ..models.media import MediaAsset
from ..models.user import User

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_RESERVED = frozenset({"www", "api", "admin", "portal", "app"})


def validate_tenant_slug(slug: str) -> str:
    s = slug.strip().lower()
    if not s or not _SLUG_RE.match(s):
        raise ValueError("tenant_slug must be lowercase alphanumeric with optional hyphens.")
    if s in _RESERVED:
        raise ValueError(f"tenant_slug '{s}' is reserved.")
    return s


def _slug_from_email(email: str | None) -> str:
    if not email or "@" not in email:
        return settings.default_media_tenant_slug
    local = email.split("@")[0].lower()
    cleaned = re.sub(r"[^a-z0-9]+", "", local)[:40]
    if not cleaned:
        return settings.default_media_tenant_slug
    try:
        return validate_tenant_slug(cleaned)
    except ValueError:
        return settings.default_media_tenant_slug


def _unique_slug(db: Session, base: str) -> str:
    candidate = validate_tenant_slug(base)
    if not db.query(Artist).filter(Artist.tenant_slug == candidate).first():
        return candidate
    for i in range(2, 100):
        alt = f"{candidate}-{i}"
        if len(alt) > 63:
            alt = f"{candidate[:50]}-{i}"
        try:
            alt = validate_tenant_slug(alt)
        except ValueError:
            continue
        if not db.query(Artist).filter(Artist.tenant_slug == alt).first():
            return alt
    raise ValueError("Could not allocate a unique tenant_slug.")


def _claim_markers() -> list[str]:
    raw = (settings.primary_artist_claim_email_markers or "").strip()
    if not raw:
        return ["phillip", "phillipjames.com"]
    return [m.strip().lower() for m in raw.split(",") if m.strip()]


def _allowed_claim_subs() -> set[str]:
    raw = (settings.primary_artist_claim_auth0_subs or "").strip()
    if not raw:
        return set()
    return {s.strip() for s in raw.split(",") if s.strip()}


def user_may_claim_default_tenant_workspace(user: User) -> bool:
    """True if this login may take over the seeded default tenant (e.g. Phillip James in dev)."""
    sub = (user.auth0_sub or "").strip()
    if sub and sub in _allowed_claim_subs():
        return True
    email = (user.email or "").lower()
    for marker in _claim_markers():
        if marker and marker in email:
            return True
    return False


def _display_name_for_user(user: User, slug: str) -> str:
    name = (user.name or "").strip()
    if not name or name.lower() in {"user", "unknown", "anonymous"}:
        return slug.replace("-", " ").title()
    return name


def get_artist_by_sub(db: Session, auth0_sub: str) -> Artist | None:
    return db.query(Artist).filter(Artist.auth0_sub == auth0_sub).first()


def get_artist_by_slug(db: Session, tenant_slug: str) -> Artist | None:
    return db.query(Artist).filter(Artist.tenant_slug == tenant_slug).first()


def _merge_stray_artist_into_canonical(db: Session, *, dup: Artist, canonical: Artist, user: User) -> None:
    """Move assets keyed by Auth0 sub onto canonical tenant; delete duplicate Artist row."""
    sub = user.auth0_sub or ""
    wrong_slug = dup.tenant_slug
    canon_slug = canonical.tenant_slug
    db.query(MediaAsset).filter(
        MediaAsset.created_by == sub,
        MediaAsset.tenant_slug == wrong_slug,
        MediaAsset.is_deleted.is_(False),
    ).update({MediaAsset.tenant_slug: canon_slug}, synchronize_session=False)
    db.delete(dup)
    db.flush()
    canonical.auth0_sub = sub
    if user.name and user.name.strip():
        canonical.display_name = user.name.strip()


def get_or_create_artist(db: Session, user: User) -> Artist:
    sub = user.auth0_sub
    if not sub:
        raise ValueError("User has no auth0_sub")

    canon = settings.default_media_tenant_slug.strip().lower()
    canonical = get_artist_by_slug(db, canon)
    existing = get_artist_by_sub(db, sub)

    # One-time: bind the primary (seeded) tenant row to this Auth0 user and fold stray profiles.
    if (
        user_may_claim_default_tenant_workspace(user)
        and canonical is not None
        and (canonical.auth0_sub or "").startswith("seed:")
    ):
        if existing is None:
            canonical.auth0_sub = sub
            if user.name and user.name.strip():
                canonical.display_name = user.name.strip()
            db.commit()
            db.refresh(canonical)
            return canonical
        if existing.id != canonical.id:
            _merge_stray_artist_into_canonical(db, dup=existing, canonical=canonical, user=user)
            db.commit()
            db.refresh(canonical)
            return canonical

    if existing:
        return existing

    email = (user.email or "").lower()
    if "phillip" in email or email.endswith("@phillipjames.com"):
        base = settings.default_media_tenant_slug
    else:
        base = _slug_from_email(email)

    slug = _unique_slug(db, base)
    display = _display_name_for_user(user, slug)

    artist = Artist(
        auth0_sub=sub,
        tenant_slug=slug,
        display_name=display,
        epk_config=default_epk_config(),
    )
    db.add(artist)
    db.commit()
    db.refresh(artist)
    return artist


def tenant_slug_for_user(db: Session, user: User) -> str:
    """Resolved tenant for storage + API scoping (provisions artist if needed)."""
    return get_or_create_artist(db, user).tenant_slug
