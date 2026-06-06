"""Whitelisted manager agent tools — definitions and dispatch only."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ..models.artist import Artist
from ..models.manager import ManagerThread

logger = logging.getLogger(__name__)

MANAGER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "reply_to_artist",
            "description": "Send a conversational reply (advice, Q&A, planning).",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Reply text for the artist."},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_epk_from_vision",
            "description": (
                "Build an HTML/CSS EPK MVP from the active vision pack (wireframe, references, media) "
                "and artist spec. Runs render + vision critique loop."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "vision_id": {"type": "string", "description": "Workbench vision group id."},
                    "spec": {
                        "type": "string",
                        "description": "Design brief / spec for the press kit.",
                    },
                },
                "required": ["vision_id", "spec"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_epk_draft",
            "description": (
                "Update the EPK draft preview (layout, theme, copy). Does not publish live. "
                "Use when the artist asks to change how their press kit looks or reads."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Clear design/copy instruction for the EPK builder.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
]

ALLOWED_TOOL_NAMES = frozenset({"reply_to_artist", "update_epk_draft", "build_epk_from_vision"})


@dataclass
class ToolExecutionResult:
    reply: str
    metadata: dict[str, Any] | None = None
    tool_used: str | None = None
    draft_updated: bool = False
    iteration_id: str | None = None
    reasoning_summary: str | None = None


def execute_tool(
    name: str,
    args: dict[str, Any],
    *,
    db: Session,
    artist: Artist,
    thread: ManagerThread,
    user_message: str,
) -> ToolExecutionResult:
    if name not in ALLOWED_TOOL_NAMES:
        logger.warning(
            "Manager agent disallowed tool tenant=%s thread=%s tool=%s",
            artist.tenant_slug,
            thread.id,
            name,
        )
        return ToolExecutionResult(
            reply="I can help with manager advice or EPK preview updates — what would you like to do?",
        )

    if name == "reply_to_artist":
        text = (args.get("message") or "").strip()
        return ToolExecutionResult(
            reply=text or "How can I help with your EPK or next steps?",
            tool_used="reply_to_artist",
        )

    if name == "build_epk_from_vision":
        from .epk_build_loop import build_epk_from_vision as run_build

        vision_id = (args.get("vision_id") or thread.vision_id or "").strip()
        spec = (args.get("spec") or user_message).strip()
        if not vision_id:
            return ToolExecutionResult(
                reply="Select a vision group in the EPK builder first, then ask to build.",
                tool_used="build_epk_from_vision",
            )
        if not spec:
            return ToolExecutionResult(
                reply="Add a design spec describing the EPK you want.",
                tool_used="build_epk_from_vision",
            )
        result = run_build(db, artist, thread, vision_id=vision_id, spec=spec)
        reply = result.get("reasoning_summary") or "Built EPK preview."
        critique = result.get("critique_summary")
        if critique:
            reply = f"{reply}\n\n{critique}"
        return ToolExecutionResult(
            reply=reply,
            metadata={
                "iteration_id": result.get("iteration_id"),
                "type": "epk_build",
                "match_score": result.get("match_score"),
                "revision_cycles": result.get("revision_cycles"),
            },
            tool_used="build_epk_from_vision",
            draft_updated=True,
            iteration_id=result.get("iteration_id"),
            reasoning_summary=result.get("reasoning_summary"),
        )

    if name == "update_epk_draft":
        from .manager_epk_service import apply_epk_update_from_chat

        prompt = (args.get("prompt") or user_message).strip()
        if not prompt:
            return ToolExecutionResult(
                reply="Tell me what you'd like changed on your EPK preview.",
                tool_used="update_epk_draft",
            )
        summary, iteration = apply_epk_update_from_chat(db, artist, thread, prompt)
        reasoning = summary or "Draft updated."
        return ToolExecutionResult(
            reply=summary,
            metadata={
                "iteration_id": iteration.id,
                "type": "epk_generate",
                "source": "manager_chat",
            },
            tool_used="update_epk_draft",
            draft_updated=True,
            iteration_id=iteration.id,
            reasoning_summary=reasoning,
        )

    return ToolExecutionResult(reply="Something went wrong — please try again.")
