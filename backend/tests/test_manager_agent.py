"""Tests for scoped manager agent tool routing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.manager_agent import run_manager_turn
from app.services.manager_llm import generate_manager_reply, manager_llm_configured, parse_prompt_tool_call
from app.services.manager_tools import ToolExecutionResult


class _FakeArtist:
    tenant_slug = "phillipjames"
    display_name = "Phillip James"
    epk_config = {"tagline": "Outlaw country", "bio": "Singer-songwriter"}
    manager_system_prompt = None
    allow_training_contribution = False
    epk_draft = None


class _FakeThread:
    id = "thread-1"
    mode = "general"


class _FakeThreadEpk:
    id = "thread-epk"
    mode = "epk_builder"


def test_stub_path_returns_usable_message():
    with patch("app.services.manager_llm.settings") as mock_settings:
        mock_settings.manager_llm_provider = ""
        mock_settings.openrouter_api_key = ""
        mock_settings.openai_api_key = ""
        mock_settings.anthropic_api_key = ""
        assert manager_llm_configured() is False
        reply = generate_manager_reply("system", "hello")
        assert reply
        assert "OPENROUTER" in reply or "configured" in reply.lower()


def test_parse_prompt_tool_call():
    parsed = parse_prompt_tool_call(
        '{"tool":"reply_to_artist","args":{"message":"Hello"}}'
    )
    assert parsed == ("reply_to_artist", {"message": "Hello"})


def test_native_reply_to_artist_tool():
    db = MagicMock()
    artist = _FakeArtist()
    thread = _FakeThread()
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "reply_to_artist",
                                "arguments": '{"message": "Upload a hero photo next."}',
                            }
                        }
                    ]
                }
            }
        ]
    }
    with patch("app.services.manager_agent.manager_llm_configured", return_value=True), patch(
        "app.services.manager_agent.resolved_manager_tool_mode",
        return_value="native",
    ), patch("app.services.manager_agent.openrouter_chat", return_value=response):
        turn = run_manager_turn(db, artist, thread, "what should I upload?", [])
    assert turn.reply == "Upload a hero photo next."
    assert turn.draft_updated is False
    assert turn.tool_used == "reply_to_artist"


def test_prompt_mode_update_epk_draft():
    db = MagicMock()
    artist = _FakeArtist()
    thread = _FakeThreadEpk()
    response = {
        "choices": [
            {
                "message": {
                    "content": '{"tool":"update_epk_draft","args":{"prompt":"dark minimal country EPK"}}',
                }
            }
        ]
    }
    with patch("app.services.manager_agent.manager_llm_configured", return_value=True), patch(
        "app.services.manager_agent.resolved_manager_tool_mode",
        return_value="prompt",
    ), patch("app.services.manager_agent.openrouter_chat", return_value=response), patch(
        "app.services.manager_agent.execute_tool",
        return_value=ToolExecutionResult(
            reply="Updated theme to dark browns.",
            tool_used="update_epk_draft",
            draft_updated=True,
            iteration_id="iter-1",
            reasoning_summary="Updated theme to dark browns.",
            metadata={"iteration_id": "iter-1", "type": "epk_generate", "source": "manager_chat"},
        ),
    ):
        turn = run_manager_turn(db, artist, thread, "dark minimal country EPK", [])
    assert turn.draft_updated is True
    assert turn.iteration_id == "iter-1"
    assert turn.tool_used == "update_epk_draft"


def test_epk_builder_no_tool_call_does_not_update_draft():
    db = MagicMock()
    artist = _FakeArtist()
    thread = _FakeThreadEpk()
    plain_response = {
        "choices": [
            {
                "message": {
                    "content": "Sure — tell me more about the vibe you want.",
                    "tool_calls": [],
                }
            }
        ]
    }
    with patch("app.services.manager_agent.manager_llm_configured", return_value=True), patch(
        "app.services.manager_agent.resolved_manager_tool_mode",
        return_value="native",
    ), patch("app.services.manager_agent.openrouter_chat", return_value=plain_response), patch(
        "app.services.manager_agent.execute_tool"
    ) as mock_execute:
        turn = run_manager_turn(db, artist, thread, "make it darker", [])
    assert turn.draft_updated is False
    mock_execute.assert_not_called()


def test_unknown_tool_safe_fallback():
    db = MagicMock()
    artist = _FakeArtist()
    thread = _FakeThread()
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"function": {"name": "run_shell", "arguments": "{}"}},
                    ]
                }
            }
        ]
    }
    with patch("app.services.manager_agent.manager_llm_configured", return_value=True), patch(
        "app.services.manager_agent.resolved_manager_tool_mode",
        return_value="native",
    ), patch("app.services.manager_agent.openrouter_chat", return_value=response):
        turn = run_manager_turn(db, artist, thread, "hello", [])
    assert "EPK preview" in turn.reply or "manager advice" in turn.reply
