## EPK HTML GENERATION

Generate a press-kit page as sanitized HTML and CSS. Use workbench media via `asset_bindings` keys referenced in HTML as `{{binding_key}}`.

Respond ONLY with valid JSON (no markdown fences):
{
  "reasoning_summary": "1-2 sentences for the artist",
  "html": "<main>...</main>",
  "css": "body { ... }",
  "asset_bindings": { "hero_photo": "<asset_uuid>", "track_1": "<asset_uuid>" }
}

Rules:
- No `<script>`, inline event handlers, or external `@import`.
- Mobile-friendly layout; semantic HTML.
- Match the artist spec and reference the wireframe layout structure when provided.
- Bind only asset ids from the supplied media list.
- Keep CSS in the css field, not inline styles except rare cases.
