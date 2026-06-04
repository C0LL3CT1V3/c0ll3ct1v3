# Scoped manager agent

The portal manager runs **inside the backend** — no external agent gateway, no shell tools, no filesystem access.

## Brain

Set on the API server only (`backend/.env`):

```bash
OPENROUTER_API_KEY=sk-or-v1-...
MANAGER_LLM_PROVIDER=openrouter
MANAGER_LLM_MODEL=anthropic/claude-3.5-haiku
MANAGER_CHAT_RATE_LIMIT_PER_MIN=20
```

OpenRouter is OpenAI-compatible; the key never reaches the browser.

## Tool dispatch (`MANAGER_TOOL_MODE`)

| Mode | When | How |
|------|------|-----|
| `auto` (default) | Qwen models | JSON tool object in model output (fine-tune friendly) |
| `auto` | Claude / GPT | OpenRouter native tools API |
| `prompt` | Force JSON tools | Always `{"tool":"...","args":{...}}` — use for Qwen fine-tuning |
| `native` | Force OpenRouter tools | Requires model with tool-use support |

Prompt-mode schema: `backend/app/prompts/manager_chat_tools_prompt.md`

## Permissions (whitelisted tools)

| Tool | What it does |
|------|----------------|
| `reply_to_artist` | Conversational manager advice |
| `update_epk_draft` | JSON patch → Postgres `epk_draft` preview (does **not** publish) |

One tool call per chat turn. Unknown tools are rejected.

Scope rules: `backend/app/prompts/manager_agent_scope.md`  
Chat persona: `backend/app/prompts/manager_chat_persona.md` (no raw JSON)  
EPK patch schema: `backend/app/prompts/manager_epk_patch.md`

## Flow

```
Portal POST /manager/chat
  → Auth0 tenant binding + rate limit
  → manager_agent.run_manager_turn()
  → OpenRouter (tools)
  → optional internal EPK patch
  → thread messages in Postgres
```

EPK Builder passes `mode=epk_builder`. Frontend refreshes preview only when `draft_updated: true`.

## Verify

```bash
# After restarting backend
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/manager/status
```

Expect `{ "configured": true, "provider": "openrouter", "model": "..." }`.

## Manual acceptance

**Functional**

1. Portal Manager → Q&A returns natural language (no JSON blobs)
2. EPK Builder → design prompt updates preview when `draft_updated`
3. EPK Builder → question with no tool call leaves preview unchanged
4. Publish still required for live EPK

**Quality (subjective)**

- [ ] “dark minimal country EPK” → bio/headline suitable for a real press kit
- [ ] Theme direction matches prompt
- [ ] “make headline larger” adjusts hero, not a random block

## Fallback

Without `OPENROUTER_API_KEY`, chat returns a stub message and EPK iterate uses heuristic patches.

## CLI

`scripts/manager_epk.py` calls `/manager/*` with `C0LL3CT1V3_AGENT_KEY` — dev only, not required for portal.
