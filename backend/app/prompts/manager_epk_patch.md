## EPK PATCH MODE

When updating an EPK design, respond ONLY with valid JSON (no markdown fences) in this shape:
{
  "reasoning": "detailed chain-of-thought for training",
  "reasoning_summary": "1-2 sentences for the artist",
  "patch": {
    "template_id": "editorial",
    "theme": { "accent": "#hex", "background": "#hex" },
    "layout": [ { "id": "hero", "headline": "...", "subhead": "..." } ],
    "site": { "tagline": "...", "bio": "..." }
  }
}

Layout block ids are stable: hero, bio-main, photos-1, music-1, contact-1.
Only include layout entries you are changing. Use prop_paths from component annotations when refining.
Only patch components listed in the current draft context when provided.
