## EPK VISION CRITIQUE

Compare the generated EPK screenshot against the wireframe, reference images, and artist spec. Focus on major layout/structure gaps only — not pixel-perfect polish.

Respond ONLY with valid JSON:
{
  "match_score": 0.0,
  "major_gaps": ["..."],
  "minor_gaps": ["..."],
  "should_revise": false,
  "critique_summary": "1-2 sentences"
}

Set should_revise true only when major_gaps would confuse a booker (missing hero, wrong section order, unreadable text). Do not revise for minor styling differences.

Note typography mismatches (wrong font mood, illegible pairing) in `minor_gaps` when a `font_palette` was supplied.
