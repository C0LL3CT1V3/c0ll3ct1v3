"""Manager chat — LLM when configured, deterministic stub otherwise."""

from __future__ import annotations

import os
from pathlib import Path

from ..config import settings

_STUB_REPLY = (
    "Manager is not configured yet. Set MANAGER_LLM_PROVIDER and OPENAI_API_KEY "
    "(or ANTHROPIC_API_KEY) on the API server to enable live responses."
)


def _manager_identity_path() -> Path:
    # workspace/manager_identity.md (repo root is parent of c0ll3ct1v3)
    return Path(__file__).resolve().parents[4] / "manager_identity.md"


def load_manager_identity_template() -> str:
    path = _manager_identity_path()
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "You are the c0ll3ct1v3 artist manager: practical, warm, and action-oriented."


def _audience_profile_summary(epk_config: dict) -> str:
    ap = epk_config.get("audience_profile")
    if not isinstance(ap, dict):
        return ""
    lines = [
        f"Primary genre: {ap.get('primary_genre', '')}",
        f"Pitch line: {ap.get('pitch_line', '')}",
    ]
    tiers = ap.get("tiers") or {}
    for tier_key, label in [
        ("aspiration", "Established comps"),
        ("engagement", "Engagement comps"),
        ("peer", "Peer comps"),
    ]:
        names = [a.get("name") for a in tiers.get(tier_key, []) if a.get("name")][:6]
        if names:
            lines.append(f"{label}: {', '.join(names)}")
    actions = ap.get("actions") or []
    if actions:
        lines.append("Audience actions: " + "; ".join(actions[:4]))
    return "\n".join(lines)


def build_system_prompt(artist_display_name: str, epk_config: dict, override: str | None) -> str:
    base = override.strip() if override else load_manager_identity_template()
    tagline = epk_config.get("tagline") or ""
    bio = epk_config.get("bio") or ""
    audience = _audience_profile_summary(epk_config)
    audience_block = f"\nAudience map (use for marketing advice):\n{audience}\n" if audience else ""
    return (
        f"{base}\n\n"
        f"Current artist: {artist_display_name}\n"
        f"Tagline: {tagline}\n"
        f"Bio: {bio}\n"
        f"{audience_block}"
        "You are in conversation-only mode (no tools) for v1."
    )


def generate_manager_reply(system_prompt: str, user_message: str) -> str:
    provider = (os.environ.get("MANAGER_LLM_PROVIDER") or "").strip().lower()

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return _STUB_REPLY
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=800,
            )
            return (resp.choices[0].message.content or "").strip() or _STUB_REPLY
        except Exception:
            return _STUB_REPLY

    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            return _STUB_REPLY
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
            msg = client.messages.create(
                model=model,
                max_tokens=800,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            parts = [b.text for b in msg.content if hasattr(b, "text")]
            return "\n".join(parts).strip() or _STUB_REPLY
        except Exception:
            return _STUB_REPLY

    # No provider configured
    _ = settings
    return _STUB_REPLY
