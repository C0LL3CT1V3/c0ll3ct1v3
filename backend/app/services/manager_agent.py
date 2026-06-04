"""Scoped in-process manager agent — OpenRouter brain, whitelisted tools only."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..models.artist import Artist
from ..models.manager import ManagerThread
from .manager_llm import (
    build_system_prompt,
    load_chat_tools_prompt_template,
    manager_llm_configured,
    openrouter_chat,
    parse_prompt_tool_call,
    resolved_manager_tool_mode,
    user_facing_openrouter_error,
)
from .manager_tools import ALLOWED_TOOL_NAMES, MANAGER_TOOLS, ToolExecutionResult, execute_tool

logger = logging.getLogger(__name__)


@dataclass
class ManagerTurnResult:
    reply: str
    metadata: dict[str, Any] | None = None
    draft_updated: bool = False
    iteration_id: str | None = None
    reasoning_summary: str | None = None
    tool_used: str | None = None


def _scope_prompt() -> str:
    path = settings.manager_agent_scope_path()
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "Use only the provided tools. Stay within artist manager scope."


def _turn_result_from_tool(result: ToolExecutionResult) -> ManagerTurnResult:
    return ManagerTurnResult(
        reply=result.reply,
        metadata=result.metadata,
        draft_updated=result.draft_updated,
        iteration_id=result.iteration_id,
        reasoning_summary=result.reasoning_summary,
        tool_used=result.tool_used,
    )


def _build_messages(
    artist: Artist,
    thread: ManagerThread,
    user_message: str,
    history: list[dict[str, str]],
    *,
    context_block: str = "",
    tool_mode: str,
) -> tuple[list[dict[str, Any]], str]:
    epk = artist.epk_config or {}
    identity = build_system_prompt(
        artist.display_name,
        epk,
        artist.manager_system_prompt,
        prompt_role="chat",
    )
    system = f"{identity}\n\n{_scope_prompt()}"
    if tool_mode == "prompt":
        system += f"\n\n{load_chat_tools_prompt_template()}"
    if context_block.strip():
        system += f"\n\n{context_block.strip()}"

    mode = thread.mode or "general"
    if mode == "epk_builder":
        system += (
            "\n\nThread mode: epk_builder. You MUST call a tool on every turn. "
            "Prefer `update_epk_draft` for design/copy changes; use `reply_to_artist` for questions only."
        )

    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for item in history[-12:]:
        role = item.get("role")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": item.get("content") or ""})
    messages.append({"role": "user", "content": user_message})
    return messages, mode


def _dispatch_tool(
    name: str,
    args: dict[str, Any],
    *,
    db: Session,
    artist: Artist,
    thread: ManagerThread,
    user_message: str,
    mode: str,
) -> ManagerTurnResult:
    if name not in ALLOWED_TOOL_NAMES:
        logger.warning(
            "Manager agent unknown tool tenant=%s thread=%s tool=%s",
            artist.tenant_slug,
            thread.id,
            name,
        )
        return ManagerTurnResult(
            reply="I can help with manager advice or EPK preview updates — what would you like to do?",
        )

    logger.info(
        "Manager agent tool tenant=%s thread=%s mode=%s tool=%s",
        artist.tenant_slug,
        thread.id,
        mode,
        name,
    )
    return _turn_result_from_tool(
        execute_tool(
            name,
            args,
            db=db,
            artist=artist,
            thread=thread,
            user_message=user_message,
        )
    )


def _run_native_tool_turn(
    messages: list[dict[str, Any]],
    *,
    db: Session,
    artist: Artist,
    thread: ManagerThread,
    user_message: str,
    mode: str,
) -> ManagerTurnResult | None:
    """Returns None if model did not produce a native tool call (caller may retry prompt mode)."""
    response = openrouter_chat(messages=messages, tools=MANAGER_TOOLS, tool_choice="auto")
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    tool_calls = message.get("tool_calls") or []

    if not tool_calls:
        content = (message.get("content") or "").strip()
        if not content:
            return None
        if mode == "epk_builder":
            logger.warning(
                "Manager agent epk_builder turn without tool call tenant=%s thread=%s",
                artist.tenant_slug,
                thread.id,
            )
        return ManagerTurnResult(reply=content)

    if len(tool_calls) > 1:
        logger.warning(
            "Manager agent returned multiple tool calls tenant=%s thread=%s count=%s",
            artist.tenant_slug,
            thread.id,
            len(tool_calls),
        )

    call = tool_calls[0]
    fn = call.get("function") or {}
    name = (fn.get("name") or "").strip()
    try:
        args = json.loads(fn.get("arguments") or "{}")
    except json.JSONDecodeError:
        args = {}
    return _dispatch_tool(
        name,
        args,
        db=db,
        artist=artist,
        thread=thread,
        user_message=user_message,
        mode=mode,
    )


def _run_prompt_tool_turn(
    messages: list[dict[str, Any]],
    *,
    db: Session,
    artist: Artist,
    thread: ManagerThread,
    user_message: str,
    mode: str,
) -> ManagerTurnResult:
    response = openrouter_chat(messages=messages, json_mode=False)
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = (message.get("content") or "").strip()

    parsed = parse_prompt_tool_call(content)
    if parsed:
        name, args = parsed
        return _dispatch_tool(
            name,
            args,
            db=db,
            artist=artist,
            thread=thread,
            user_message=user_message,
            mode=mode,
        )

    reply = content or "I didn't catch that — could you rephrase?"
    if mode == "epk_builder":
        logger.warning(
            "Manager agent prompt mode missing tool JSON tenant=%s thread=%s",
            artist.tenant_slug,
            thread.id,
        )
    return ManagerTurnResult(reply=reply)


def run_manager_turn(
    db: Session,
    artist: Artist,
    thread: ManagerThread,
    user_message: str,
    history: list[dict[str, str]],
    *,
    context_block: str = "",
) -> ManagerTurnResult:
    """One bounded agent turn: at most one tool call, only whitelisted tools."""
    if not manager_llm_configured():
        from .manager_llm import generate_manager_reply

        epk = artist.epk_config or {}
        system = build_system_prompt(
            artist.display_name,
            epk,
            artist.manager_system_prompt,
            prompt_role="chat",
        )
        reply = generate_manager_reply(system, user_message, history=history)
        return ManagerTurnResult(reply=reply)

    tool_mode = resolved_manager_tool_mode()
    messages, mode = _build_messages(
        artist,
        thread,
        user_message,
        history,
        context_block=context_block,
        tool_mode=tool_mode,
    )

    try:
        if tool_mode == "prompt":
            return _run_prompt_tool_turn(
                messages,
                db=db,
                artist=artist,
                thread=thread,
                user_message=user_message,
                mode=mode,
            )

        native_result = _run_native_tool_turn(
            messages,
            db=db,
            artist=artist,
            thread=thread,
            user_message=user_message,
            mode=mode,
        )
        if native_result is not None:
            return native_result

        # Native mode returned plain text without tools — retry prompt mode (Qwen, etc.).
        logger.info(
            "Manager agent falling back to prompt tool mode tenant=%s model=%s",
            artist.tenant_slug,
            settings.manager_llm_model,
        )
        messages, mode = _build_messages(
            artist,
            thread,
            user_message,
            history,
            context_block=context_block,
            tool_mode="prompt",
        )
        return _run_prompt_tool_turn(
            messages,
            db=db,
            artist=artist,
            thread=thread,
            user_message=user_message,
            mode=mode,
        )
    except Exception as exc:
        detail = str(exc)
        logger.warning("Manager agent LLM call failed tenant=%s: %s", artist.tenant_slug, detail)
        if "tool use" in detail.lower():
            messages, mode = _build_messages(
                artist,
                thread,
                user_message,
                history,
                context_block=context_block,
                tool_mode="prompt",
            )
            try:
                return _run_prompt_tool_turn(
                    messages,
                    db=db,
                    artist=artist,
                    thread=thread,
                    user_message=user_message,
                    mode=mode,
                )
            except Exception as retry_exc:
                logger.warning("Manager prompt tool retry failed tenant=%s: %s", artist.tenant_slug, retry_exc)
                detail = str(retry_exc)
        return ManagerTurnResult(reply=user_facing_openrouter_error(detail))
