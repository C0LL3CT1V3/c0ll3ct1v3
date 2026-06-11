## MUSICIAN PROFILE HTML GENERATION

Generate a fan-facing musician profile page (MySpace energy) as sanitized HTML and CSS. Use workbench media via `asset_bindings` keys referenced in HTML as `{{binding_key}}`.

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
- **One scrollable musician page** — personality first; music playable without hunting.
- When `epk_readiness` is provided, include **ready/partial** sections and tasteful placeholders for **missing** items (never invent fake stats or quotes).
- Required when assets exist: music player near top, about section, photo wall, social/streaming links.
- Optional: live video embed, booking/contact footer.
- When a `font_palette` is provided, use those Google Font families in CSS (`font-family` on `body`, headings, nav, quotes). Example: `body { font-family: 'Inter', sans-serif; }` and `h1, h2 { font-family: 'Playfair Display', serif; }`.
- Do not add `<link>` tags for fonts — the sim renderer injects Google Fonts automatically from the palette.
