## EPK FONT DETECTION

Study the reference images (and wireframe if provided) to infer the typography direction for an artist press kit page.

Pick the closest **Google Fonts** matches for:
- `heading` — display / title type (often serif or bold sans)
- `body` — paragraph and UI text (readable sans or serif)
- `accent` — optional labels, quotes, or nav (may match heading or body)

Respond ONLY with valid JSON:
{
  "heading": {
    "family": "Playfair Display",
    "google_fonts_family": "Playfair+Display",
    "weights": ["700"],
    "category": "serif",
    "confidence": 0.85
  },
  "body": {
    "family": "Inter",
    "google_fonts_family": "Inter",
    "weights": ["400", "600"],
    "category": "sans-serif",
    "confidence": 0.9
  },
  "accent": null,
  "notes": "1 sentence on typographic mood"
}

Rules:
- Use real Google Fonts families only (`google_fonts_family` is the URL slug, spaces as `+`).
- `weights` must be strings like "400", "600", "700".
- If references disagree, favor the dominant mood; lower confidence when uncertain.
- Omit `accent` or set null when not distinct from heading/body.
