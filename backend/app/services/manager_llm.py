"""Manager chat — OpenRouter (default), optional OpenAI/Anthropic, stub otherwise."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Literal

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_STUB_REPLY = (
    "Manager is not configured yet. Set OPENROUTER_API_KEY on the API server "
    "(or MANAGER_LLM_PROVIDER=openai with OPENAI_API_KEY)."
)


def _prompt_path(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "prompts" / name


def _load_prompt_file(name: str, fallback: str) -> str:
    path = _prompt_path(name)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return fallback


def load_manager_identity_template() -> str:
    return _load_prompt_file(
        "manager_identity.md",
        "You are the c0ll3ct1v3 artist manager: practical, warm, and action-oriented.",
    )


def load_chat_persona_template() -> str:
    return _load_prompt_file("manager_chat_persona.md", "Use the provided tools for every response.")


def load_epk_patch_template() -> str:
    return _load_prompt_file("manager_epk_patch.md", "Return JSON with reasoning, reasoning_summary, and patch.")


def load_epk_html_generate_template() -> str:
    return _load_prompt_file(
        "manager_epk_html_generate.md",
        "Return JSON with reasoning_summary, html, css, asset_bindings.",
    )


def load_epk_vision_critique_template() -> str:
    return _load_prompt_file(
        "manager_epk_vision_critique.md",
        "Return JSON with match_score, major_gaps, minor_gaps, should_revise, critique_summary.",
    )


def _manager_identity_path() -> Path:
    return _prompt_path("manager_identity.md")


def _effective_provider() -> str:
    explicit = (settings.manager_llm_provider or "").strip().lower()
    if explicit:
        return explicit
    if (settings.openrouter_api_key or "").strip():
        return "openrouter"
    if (settings.openai_api_key or "").strip():
        return "openai"
    if (settings.anthropic_api_key or "").strip():
        return "anthropic"
    return ""


def manager_llm_configured() -> bool:
    provider = _effective_provider()
    if provider == "openrouter":
        return bool((settings.openrouter_api_key or "").strip())
    if provider == "openai":
        return bool((settings.openai_api_key or "").strip())
    if provider == "anthropic":
        return bool((settings.anthropic_api_key or "").strip())
    return False


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


def resolved_manager_model() -> str:
    explicit = (settings.manager_llm_model or "").strip()
    if explicit:
        return explicit
    fallback = (settings.openrouter_model or "").strip()
    return fallback or "anthropic/claude-3.5-haiku"


def load_chat_tools_prompt_template() -> str:
    return _load_prompt_file(
        "manager_chat_tools_prompt.md",
        'Return JSON: {"tool":"reply_to_artist","args":{"message":"..."}}',
    )


def resolved_manager_tool_mode() -> str:
    explicit = (settings.manager_tool_mode or "").strip().lower()
    if explicit in ("native", "prompt"):
        return explicit
    model = resolved_manager_model().lower()
    if model.startswith("qwen/") or "qwen-" in model:
        return "prompt"
    return "native"


def effective_manager_provider() -> str:
    return _effective_provider()


def parse_prompt_tool_call(text: str) -> tuple[str, dict[str, Any]] | None:
    """Parse prompt-mode tool JSON: {"tool": "...", "args": {...}}."""
    parsed = _parse_json_response(text)
    if not parsed:
        return None
    name = (parsed.get("tool") or parsed.get("name") or "").strip()
    args = parsed.get("args") or parsed.get("arguments") or {}
    if not name or not isinstance(args, dict):
        return None
    return name, args


def build_system_prompt(
    artist_display_name: str,
    epk_config: dict,
    override: str | None,
    *,
    prompt_role: Literal["chat", "patch"] = "chat",
) -> str:
    base = override.strip() if override else load_manager_identity_template()
    role_block = load_chat_persona_template() if prompt_role == "chat" else load_epk_patch_template()
    tagline = epk_config.get("tagline") or ""
    bio = epk_config.get("bio") or ""
    audience = _audience_profile_summary(epk_config)
    audience_block = f"\nAudience map (use for marketing advice):\n{audience}\n" if audience else ""
    return (
        f"{base}\n\n{role_block}\n\n"
        f"Current artist: {artist_display_name}\n"
        f"Tagline: {tagline}\n"
        f"Bio: {bio}\n"
        f"{audience_block}"
    )


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _openrouter_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.openrouter_api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://c0ll3ct1v3.xyz",
        "X-Title": "c0ll3ct1v3 Manager",
    }


def user_facing_openrouter_error(detail: str) -> str:
    lowered = detail.lower()
    if "rate-limited" in lowered or "429" in lowered:
        return "The AI provider is briefly rate-limited. Wait a few seconds and try again."
    if "json_object" in lowered or "response format" in lowered:
        return "The manager hit a provider compatibility issue. Retrying usually fixes it — try again."
    if "401" in lowered or "authentication" in lowered or "missing authentication" in lowered:
        return "Manager API key is invalid. Check OPENROUTER_API_KEY in backend/.env (one key only)."
    return (
        "The manager is temporarily unavailable. Check OPENROUTER_API_KEY on the API server "
        "and try again."
    )


def openrouter_chat(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict | None = None,
    json_mode: bool = False,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    api_key = (settings.openrouter_api_key or "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    body: dict[str, Any] = {
        "model": resolved_manager_model(),
        "messages": messages,
        "max_tokens": max_tokens or settings.manager_llm_max_tokens,
        "provider": {"allow_fallbacks": True},
    }
    if tools:
        body["tools"] = tools
    if tool_choice is not None:
        body["tool_choice"] = tool_choice
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    timeout = float(settings.manager_llm_timeout_seconds)
    last_error = ""
    with httpx.Client(timeout=timeout) as client:
        for attempt in range(3):
            resp = client.post(_OPENROUTER_URL, headers=_openrouter_headers(), json=body)
            if resp.status_code < 400:
                return resp.json()
            last_error = resp.text[:500]
            if resp.status_code == 429 and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            break
        raise RuntimeError(f"OpenRouter error ({resp.status_code}): {last_error}")


def _chat_text(messages: list[dict[str, Any]], *, json_mode: bool = False) -> str:
    provider = _effective_provider()
    if provider == "openrouter":
        data = openrouter_chat(messages=messages, json_mode=json_mode, max_tokens=settings.manager_llm_max_tokens)
        choice = (data.get("choices") or [{}])[0]
        return ((choice.get("message") or {}).get("content") or "").strip()

    if provider == "openai":
        api_key = (settings.openai_api_key or "").strip()
        if not api_key:
            return ""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            kwargs: dict[str, Any] = {
                "model": settings.openai_model or "gpt-4o-mini",
                "messages": messages,
                "max_tokens": settings.manager_llm_max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("OpenAI manager call failed: %s", exc)
            return ""

    return ""


def _stub_epk_patch(prompt: str, draft: dict, *, refine: bool = False) -> dict[str, Any]:
    p = prompt.lower()
    patch: dict[str, Any] = {"layout": [], "theme": {}}
    if "dark" in p or "outlaw" in p or "country" in p:
        patch["theme"] = {"accent": "#8b4513", "background": "#1a1410"}
    if "minimal" in p:
        patch["template_id"] = "minimal"
    headline = draft.get("layout", [{}])[0] if draft.get("layout") else {}
    if refine:
        patch["layout"].append({"id": "hero", "headline": headline.get("headline", "Artist"), "subhead": "Refined per your notes"})
    else:
        patch["layout"].append(
            {
                "id": "hero",
                "headline": headline.get("headline") or "Your Artist Name",
                "subhead": "Independent · Live dates · New music",
            }
        )
        if "bio" in p or "about" in p:
            patch["layout"].append({"id": "bio-main", "body": "Updated bio reflecting your prompt."})
    return {
        "reasoning": f"Stub manager applied heuristics for: {prompt[:200]}",
        "reasoning_summary": "Updated the EPK draft (stub mode — set OPENROUTER_API_KEY for live AI).",
        "patch": patch,
    }


def generate_manager_reply(
    system_prompt: str,
    user_message: str,
    history: list[dict] | None = None,
) -> str:
    if not manager_llm_configured():
        return _STUB_REPLY

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for m in history or []:
        if m.get("role") in ("user", "assistant"):
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_message})

    if _effective_provider() == "anthropic":
        api_key = (settings.anthropic_api_key or "").strip()
        if not api_key:
            return _STUB_REPLY
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            model = settings.anthropic_model or "claude-3-5-haiku-20241022"
            msg = client.messages.create(
                model=model,
                max_tokens=settings.manager_llm_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            parts = [b.text for b in msg.content if hasattr(b, "text")]
            return "\n".join(parts).strip() or _STUB_REPLY
        except Exception:
            return _STUB_REPLY

    text = _chat_text(messages)
    return text or _STUB_REPLY


def _call_llm_json(system: str, user: str, history: list[dict] | None = None) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in history or []:
        if m.get("role") in ("user", "assistant"):
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user})

    if manager_llm_configured() and _effective_provider() in ("openrouter", "openai"):
        content = _chat_text(messages, json_mode=True)
        if content:
            parsed = _parse_json_response(content)
            if parsed.get("patch") is not None:
                return parsed
    return {}


def _call_llm_json_any(
    system: str,
    user: str | list[dict[str, Any]],
    *,
    json_mode: bool = True,
    model: str | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    messages.append({"role": "user", "content": user})

    provider = _effective_provider()
    if provider == "openrouter" and (settings.openrouter_api_key or "").strip():
        chosen_model = model or resolved_manager_model()
        body: dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
            "max_tokens": max_tokens or settings.manager_llm_max_tokens,
            "provider": {"allow_fallbacks": True},
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        with httpx.Client(timeout=float(settings.manager_llm_timeout_seconds)) as client:
            resp = client.post(_OPENROUTER_URL, headers=_openrouter_headers(), json=body)
            if resp.status_code >= 400:
                logger.warning("OpenRouter JSON call failed: %s", resp.text[:300])
                return {}
            data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        content = ((choice.get("message") or {}).get("content") or "").strip()
        return _parse_json_response(content)

    if provider == "openai":
        content = _chat_text(messages, json_mode=json_mode)
        return _parse_json_response(content)
    return {}


def generate_epk_patch(
    system_prompt: str,
    user_prompt: str,
    draft: dict,
    workbench_summary: dict | None = None,
) -> dict[str, Any]:
    user = (
        f"Current EPK draft JSON:\n{json.dumps(draft, indent=2)}\n\n"
        f"Workbench assets:\n{json.dumps(workbench_summary or {}, indent=2)}\n\n"
        f"Artist request:\n{user_prompt}\n\n"
        "Return JSON with reasoning, reasoning_summary, and patch."
    )
    parsed = _call_llm_json(system_prompt, user)
    if parsed.get("patch") is not None:
        return parsed
    return _stub_epk_patch(user_prompt, draft)


def refine_epk_html_from_annotations(
    system_prompt: str,
    *,
    html: str,
    css: str,
    asset_bindings: dict[str, str],
    asset_urls: dict[str, str],
    original_prompt: str,
    resolved_annotations: list[dict],
) -> dict[str, Any]:
    user = (
        f"Original design spec: {original_prompt}\n\n"
        f"Current HTML:\n{html}\n\n"
        f"Current CSS:\n{css}\n\n"
        f"Asset bindings (placeholder key → asset id):\n{json.dumps(asset_bindings, indent=2)}\n\n"
        f"Resolvable media URLs for bindings:\n{json.dumps(asset_urls, indent=2)}\n\n"
        f"Artist annotations (bbox_norm is 0–1 relative to preview viewport):\n"
        f"{json.dumps(resolved_annotations, indent=2)}\n\n"
        "Apply the annotated feedback to the HTML/CSS. Keep existing asset binding keys where possible. "
        "Return JSON with reasoning_summary, html, css, asset_bindings."
    )
    parsed = _call_llm_json_any(
        system_prompt + "\n\nYou refine html_v1 musician profile pages from region annotations.",
        user,
        json_mode=True,
        max_tokens=4000,
    )
    if parsed.get("html"):
        return parsed
    return {
        "reasoning_summary": "Applied annotation feedback (stub mode).",
        "html": html,
        "css": css,
        "asset_bindings": asset_bindings,
    }


def refine_epk_from_annotations(
    system_prompt: str,
    draft: dict,
    original_prompt: str,
    resolved_annotations: list[dict],
) -> dict[str, Any]:
    user = (
        f"Original request: {original_prompt}\n\n"
        f"Current draft:\n{json.dumps(draft, indent=2)}\n\n"
        f"Resolved annotations:\n{json.dumps(resolved_annotations, indent=2)}\n\n"
        "Apply only the requested component changes. Return JSON with reasoning, reasoning_summary, patch."
    )
    parsed = _call_llm_json(system_prompt + "\n\nYou are refining an EPK from annotations.", user)
    if parsed.get("patch") is not None:
        return parsed
    return _stub_epk_patch(original_prompt, draft, refine=True)


def _stub_epk_html(
    spec: str,
    pack: dict,
    artist_name: str,
    font_palette: dict | None = None,
) -> dict[str, Any]:
    from .epk_font_analysis import css_font_stack, stub_font_palette

    palette = font_palette if isinstance(font_palette, dict) else stub_font_palette()
    stacks = css_font_stack(palette)
    heading_stack = stacks.get("heading", "Georgia, serif")
    body_stack = stacks.get("body", "system-ui, sans-serif")
    media = pack.get("media") or []
    bindings: dict[str, str] = {}
    if media:
        bindings["hero_photo"] = media[0]["id"]
    html = (
        f"<main class='epk'><header><h1>{artist_name}</h1>"
        f"<p>{spec[:120]}</p></header>"
        "<section class='photos'>"
        + (
            f"<img src='{{{{hero_photo}}}}' alt='Hero' />"
            if bindings
            else "<p>Add media to your vision pack.</p>"
        )
        + "</section></main>"
    )
    css = (
        f"body {{ font-family: {body_stack}; margin: 0; background: #faf9f6; color: #1a1a1a; }}"
        ".epk { max-width: 960px; margin: 0 auto; padding: 2rem; }"
        f"header h1 {{ font-family: {heading_stack}; font-size: 2.5rem; margin-bottom: 0.5rem; }}"
        ".photos img { width: 100%; border-radius: 8px; }"
    )
    return {
        "reasoning_summary": "Built a starter HTML EPK (stub mode — set OPENROUTER_API_KEY for live AI).",
        "html": html,
        "css": css,
        "asset_bindings": bindings,
    }


def generate_epk_html(
    system_prompt: str,
    *,
    spec: str,
    vision_pack: dict,
    artist_name: str = "Artist",
    critique_notes: str | None = None,
    font_palette: dict | None = None,
) -> dict[str, Any]:
    from .epk_font_analysis import css_font_stack

    template = load_epk_html_generate_template()
    stacks = css_font_stack(font_palette)
    user = (
        f"Artist spec:\n{spec}\n\n"
        f"Vision pack:\n{json.dumps(vision_pack, indent=2)}\n\n"
    )
    if font_palette:
        user += (
            f"Font palette (from reference images — use in CSS font-family):\n"
            f"{json.dumps(font_palette, indent=2)}\n\n"
            f"Suggested stacks:\n{json.dumps(stacks, indent=2)}\n\n"
        )
    readiness = vision_pack.get("epk_readiness")
    if readiness:
        user += f"EPK readiness (booker checklist — enforce in layout/copy):\n{json.dumps(readiness, indent=2)}\n\n"
    if critique_notes:
        user += f"Revision notes from vision critique:\n{critique_notes}\n\n"
    user += "Return JSON with reasoning_summary, html, css, asset_bindings."
    parsed = _call_llm_json_any(f"{system_prompt}\n\n{template}", user, json_mode=True, max_tokens=4000)
    if parsed.get("html"):
        return parsed
    return _stub_epk_html(spec, vision_pack, artist_name, font_palette)


def critique_epk_screenshot(
    *,
    spec: str,
    vision_pack: dict,
    screenshot_png: bytes | None,
) -> dict[str, Any]:
    template = load_epk_vision_critique_template()
    font_block = ""
    fp = vision_pack.get("font_palette")
    if isinstance(fp, dict):
        font_block = f"\n\nFont palette:\n{json.dumps(fp, indent=2)}"
    text_block = (
        f"Artist spec:\n{spec}\n\nVision pack metadata:\n{json.dumps(vision_pack, indent=2)}{font_block}"
    )
    user_content: list[dict[str, Any]] = [{"type": "text", "text": text_block}]

    import base64

    if screenshot_png:
        b64 = base64.standard_b64encode(screenshot_png).decode("ascii")
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    wf = vision_pack.get("wireframe")
    if wf and wf.get("preview_url"):
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": wf["preview_url"]},
            }
        )
    for ref in (vision_pack.get("references") or [])[:3]:
        if ref.get("preview_url"):
            user_content.append({"type": "image_url", "image_url": {"url": ref["preview_url"]}})

    parsed = _call_llm_json_any(
        template,
        user_content,
        json_mode=True,
        model=settings.manager_vision_model,
        max_tokens=1200,
    )
    if parsed.get("critique_summary") is not None or parsed.get("match_score") is not None:
        return parsed
    return {
        "match_score": 0.6,
        "major_gaps": [],
        "minor_gaps": [],
        "should_revise": False,
        "critique_summary": "Preview generated. Review the sim and request changes if needed.",
    }
