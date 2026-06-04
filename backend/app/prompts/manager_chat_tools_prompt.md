## Structured tool response (prompt mode)

When using prompt-based tool mode, respond with **only** a JSON object (no markdown fences):

```json
{"tool": "reply_to_artist", "args": {"message": "Your reply to the artist."}}
```

or

```json
{"tool": "update_epk_draft", "args": {"prompt": "Clear EPK design/copy instruction."}}
```

Allowed `tool` values: `reply_to_artist`, `update_epk_draft` only.
Do not emit EPK patch JSON here — `update_epk_draft` runs the builder internally.

In **epk_builder** thread mode you MUST return one of the JSON objects above on every turn.
