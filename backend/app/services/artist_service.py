"""Artist profile provisioning and tenant slug helpers."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from ..config import settings
from ..models.artist import Artist, ArtistSlugAlias, default_epk_config
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
    name = (user.name or "").lower()
    if "phillip" in name:
        return True
    return False


def _is_seed_artist(artist: Artist) -> bool:
    return (artist.auth0_sub or "").startswith("seed:")


def storage_namespace_for_artist(artist: Artist) -> str:
    """Stable workbench/S3 prefix for this artist (does not follow public slug changes)."""
    ns = (artist.storage_namespace or artist.tenant_slug or "").strip().lower()
    if not ns:
        raise ValueError("Artist has no storage namespace.")
    return ns


def _ensure_storage_namespace(db: Session, artist: Artist) -> str:
    ns = (artist.storage_namespace or "").strip().lower()
    if not ns:
        artist.storage_namespace = artist.tenant_slug
        db.flush()
        return artist.storage_namespace
    return ns


def _record_slug_alias(db: Session, artist_id: int, slug: str) -> None:
    s = slug.strip().lower()
    if not s:
        return
    exists = db.query(ArtistSlugAlias).filter(ArtistSlugAlias.slug == s).first()
    if exists:
        return
    db.add(ArtistSlugAlias(artist_id=artist_id, slug=s))


def rebind_media_to_storage_namespace(db: Session, artist: Artist) -> None:
    """Heal media rows after a public slug change (assets stay on storage_namespace)."""
    ns = _ensure_storage_namespace(db, artist)
    sub = (artist.auth0_sub or "").strip()
    if not sub:
        return
    db.query(MediaAsset).filter(
        MediaAsset.created_by == sub,
        MediaAsset.is_deleted.is_(False),
        MediaAsset.tenant_slug != ns,
    ).update({MediaAsset.tenant_slug: ns}, synchronize_session=False)


def claim_tenant_slug(
    db: Session,
    *,
    artist: Artist,
    user: User,
    new_slug: str,
) -> Artist:
    """Assign public tenant_slug, claiming a seed row when the slug is held by seed:*."""
    slug = validate_tenant_slug(new_slug)
    _ensure_storage_namespace(db, artist)
    if artist.tenant_slug == slug:
        rebind_media_to_storage_namespace(db, artist)
        return artist

    conflict = (
        db.query(Artist).filter(Artist.tenant_slug == slug, Artist.id != artist.id).first()
    )
    if conflict:
        if _is_seed_artist(conflict) and user_may_claim_default_tenant_workspace(user):
            if artist.id != conflict.id:
                _merge_stray_artist_into_canonical(db, dup=artist, canonical=conflict, user=user)
            _ensure_storage_namespace(db, conflict)
            rebind_media_to_storage_namespace(db, conflict)
            return conflict
        raise ValueError("tenant_slug already in use.")

    old_slug = artist.tenant_slug
    if old_slug and old_slug != slug:
        _record_slug_alias(db, artist.id, old_slug)
    artist.tenant_slug = slug
    rebind_media_to_storage_namespace(db, artist)
    return artist


def _display_name_for_user(user: User, slug: str) -> str:
    name = (user.name or "").strip()
    if not name or name.lower() in {"user", "unknown", "anonymous"}:
        return slug.replace("-", " ").title()
    return name


def get_artist_by_sub(db: Session, auth0_sub: str) -> Artist | None:
    return db.query(Artist).filter(Artist.auth0_sub == auth0_sub).first()


def get_artist_by_slug(db: Session, tenant_slug: str) -> Artist | None:
    return db.query(Artist).filter(Artist.tenant_slug == tenant_slug).first()


def resolve_artist_by_public_slug(db: Session, slug: str) -> Artist | None:
    """Resolve artist by current public slug or a former slug alias."""
    s = slug.strip().lower()
    artist = get_artist_by_slug(db, s)
    if artist:
        return artist
    alias = db.query(ArtistSlugAlias).filter(ArtistSlugAlias.slug == s).first()
    if not alias:
        return None
    return db.query(Artist).filter(Artist.id == alias.artist_id).first()


def _merge_stray_artist_into_canonical(db: Session, *, dup: Artist, canonical: Artist, user: User) -> None:
    """Move assets keyed by Auth0 sub onto canonical tenant; delete duplicate Artist row."""
    sub = user.auth0_sub or ""
    canon_ns = _ensure_storage_namespace(db, canonical)
    if not canonical.storage_namespace:
        canonical.storage_namespace = canon_ns
    wrong_ns = _ensure_storage_namespace(db, dup)
    db.query(MediaAsset).filter(
        MediaAsset.created_by == sub,
        MediaAsset.tenant_slug == wrong_ns,
        MediaAsset.is_deleted.is_(False),
    ).update({MediaAsset.tenant_slug: canon_ns}, synchronize_session=False)
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

    # Phillip: claim the phillipjames seed row when present (not the generic demo default).
    if user_may_claim_default_tenant_workspace(user):
        phillip_row = get_artist_by_slug(db, "phillipjames")
        if phillip_row and _is_seed_artist(phillip_row):
            if existing is None:
                phillip_row.auth0_sub = sub
                if user.name and user.name.strip():
                    phillip_row.display_name = user.name.strip()
                db.commit()
                db.refresh(phillip_row)
                return phillip_row
            if existing.id != phillip_row.id:
                _merge_stray_artist_into_canonical(
                    db, dup=existing, canonical=phillip_row, user=user
                )
                db.commit()
                db.refresh(phillip_row)
                return phillip_row

    # One-time: bind the generic seeded default tenant row to this Auth0 user and fold stray profiles.
    if (
        user_may_claim_default_tenant_workspace(user)
        and canonical is not None
        and _is_seed_artist(canonical)
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
        _ensure_storage_namespace(db, existing)
        rebind_media_to_storage_namespace(db, existing)
        db.commit()
        db.refresh(existing)
        return existing

    email = (user.email or "").lower()
    name = (user.name or "").lower()
    if (
        "phillip" in email
        or email.endswith("@phillipjames.com")
        or "phillip" in name
    ):
        base = "phillipjames"
    else:
        base = _slug_from_email(email)

    slug = _unique_slug(db, base)
    display = _display_name_for_user(user, slug)

    artist = Artist(
        auth0_sub=sub,
        tenant_slug=slug,
        storage_namespace=slug,
        display_name=display,
        epk_config=default_epk_config(),
    )
    db.add(artist)
    db.commit()
    db.refresh(artist)
    return artist


def tenant_slug_for_user(db: Session, user: User) -> str:
    """Public subdomain slug for URLs and published EPK."""
    return get_or_create_artist(db, user).tenant_slug


def storage_namespace_for_user(db: Session, user: User) -> str:
    """Immutable Vault/S3 workspace prefix (provisions artist if needed)."""
    artist = get_or_create_artist(db, user)
    return storage_namespace_for_artist(artist)
