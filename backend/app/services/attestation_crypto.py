"""RFC 8785-style canonical JSON + Ed25519 signatures for attestation claims."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ..config import settings

_DEV_KEY: Ed25519PrivateKey | None = None


def canonicalize_payload(payload: dict[str, Any]) -> bytes:
    """Deterministic JSON bytes (sorted keys, compact, UTF-8). Same fn signs and verifies."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _key_from_hex(raw: str) -> Ed25519PrivateKey:
    seed = bytes.fromhex(raw.strip())
    if len(seed) != 32:
        raise ValueError("ATTESTATION_SIGNING_KEY must be 32 bytes hex-encoded.")
    return Ed25519PrivateKey.from_private_bytes(seed)


def load_signing_key() -> Ed25519PrivateKey:
    raw = (settings.attestation_signing_key or "").strip()
    if raw:
        return _key_from_hex(raw)
    global _DEV_KEY
    if _DEV_KEY is None:
        _DEV_KEY = Ed25519PrivateKey.generate()
    return _DEV_KEY


def public_key_fingerprint(public_key: Ed25519PublicKey | None = None) -> str:
    if public_key is None:
        public_key = load_signing_key().public_key()
    der = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return hashlib.sha256(der).hexdigest()[:32]


def sign_payload(payload: dict[str, Any]) -> tuple[str, str]:
    canonical = canonicalize_payload(payload)
    digest = hashlib.sha256(canonical).digest()
    key = load_signing_key()
    sig = key.sign(digest)
    return sig.hex(), public_key_fingerprint(key.public_key())


def verify_signature(payload: dict[str, Any], signature_hex: str, fingerprint: str) -> bool:
    if not signature_hex or not fingerprint:
        return False
    key = load_signing_key()
    if public_key_fingerprint(key.public_key()) != fingerprint:
        return False
    canonical = canonicalize_payload(payload)
    digest = hashlib.sha256(canonical).digest()
    try:
        key.public_key().verify(bytes.fromhex(signature_hex), digest)
        return True
    except Exception:
        return False
