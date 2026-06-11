# Scoped manager agent

The portal manager runs **inside the backend** — no external agent gateway, no shell tools, no filesystem access.

## Brain

Set on the API server only (`backend/.env`):

```bash
OPENROUTER_API_KEY=sk-or-v1-...
MANAGER_LLM_PROVIDER=openrouter
MANAGER_LLM_MODEL=anthropic/claude-3.5-haiku
MANAGER_VISION_MODEL=google/gemini-2.0-flash-001
MANAGER_CHAT_RATE_LIMIT_PER_MIN=20
EPK_PLAYWRIGHT_ENABLED=false
EPK_SIM_BASE_URL=http://localhost:8080
EPK_BUILD_MAX_REVISIONS=2
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
| `build_epk_from_vision` | HTML/CSS MVP from vision pack + spec (Playwright + vision critique loop) |
| `update_epk_draft` | Legacy JSON layout patch (does **not** publish) |

One tool call per chat turn. Unknown tools are rejected.

Scope rules: `backend/app/prompts/manager_agent_scope.md`  
Chat persona: `backend/app/prompts/manager_chat_persona.md` (no raw JSON)  
HTML generate: `backend/app/prompts/manager_epk_html_generate.md`  
Vision critique: `backend/app/prompts/manager_epk_vision_critique.md`

## Vision pack (workbench)

Each vision group has three partitions (via `MediaAsset.tags.vision_role`):

| Role | Limit | Use |
|------|-------|-----|
| `wireframe` | 1 | Layout target for agent + critique |
| `reference` | 3 | Style / mood references |
| `media` | unlimited | Assets bound into the generated page |

API: `GET /media/visions/{id}/pack`

## EPK readiness (booker checklist)

`GET /manager/epk/completeness` and `EpkDraftOut.completeness` score the artist against press-kit essentials (music, bio, photos, video, contact, social) plus credibility/practical items (quotes, shows, rider, set lengths).

The manager agent receives gap summaries in `build_agent_context_block` and should suggest concrete next steps — uploads, copy, or spec changes — without inventing quotes or draw numbers.

## EPK build loop (html_v1)

```
Artist spec + vision pack
  → POST /manager/epk/build-from-vision (or chat tool build_epk_from_vision)
  → vision model reads reference images → Google Fonts palette
  → generate HTML/CSS (OpenRouter) using detected fonts
  → GET /manager/epk/sim/render?token=… (sandboxed iframe + Playwright)
  → vision critique (optional one revise, max EPK_BUILD_MAX_REVISIONS cycles)
  → artist reviews interactive sim
```

Draft format stored in `artist.epk_draft`:

```json
{ "format": "html_v1", "html": "...", "css": "...", "asset_bindings": {}, "vision_id": "...", "spec_snapshot": "..." }
```

Enable Playwright screenshots: `EPK_PLAYWRIGHT_ENABLED=true` and `playwright install chromium` in the backend container.

## Design history

Each build or chat-driven patch creates an `EpkIteration` row with `design_after` (full draft snapshot), optional screenshot, and critique metadata.

| Endpoint | Purpose |
|----------|---------|
| `GET /manager/epk/iterations` | List proposed designs (newest first) |
| `GET /manager/epk/iterations/{id}` | Preview a past design (iteration-scoped sim URL) |
| `POST /manager/epk/iterations/{id}/restore` | Set a past design as the current `artist.epk_draft` |

Historical `html_v1` previews use sim tokens bound to `iteration_id`, so they keep working after newer builds overwrite the live draft.

## Flow

```
Portal POST /manager/chat
  → Auth0 tenant binding + rate limit
  → manager_agent.run_manager_turn()
  → OpenRouter (tools)
  → optional internal EPK patch or build loop
  → thread messages in Postgres
```

EPK Builder passes `mode=epk_builder`. Frontend refreshes preview when `draft_updated: true` or after **Build MVP**.

## Verify

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/manager/status
```

Expect `{ "configured": true, "provider": "openrouter", "model": "..." }`.

## Manual acceptance

1. Create vision → assign wireframe, references, media in workbench
2. EPK Builder → select vision, write spec, **Build MVP**
3. Interactive sim loads in iframe; agent cycles ≤ 2
4. Chat can call `build_epk_from_vision` with same vision + spec
5. Publish still required for live EPK (html publish path TBD)

## Fallback

Without `OPENROUTER_API_KEY`, build uses stub HTML. Without Playwright, critique runs without screenshot.

## CLI

`scripts/manager_epk.py` calls `/manager/*` with `C0LL3CT1V3_AGENT_KEY` — dev only, not required for portal.
