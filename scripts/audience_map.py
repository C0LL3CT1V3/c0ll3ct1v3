#!/usr/bin/env python3
"""
Audience Mapper CLI — same logic as c0ll3ct1v3 API.

Examples:
  python3 scripts/audience_map.py --file /path/to/track.mp3
  python3 scripts/audience_map.py --file track.mp3 --out report.md
  python3 scripts/audience_map.py --api http://localhost:8080 --asset-id UUID --token "$TOKEN"
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_REPO_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


def _local_analyze(path: str, title: str | None) -> dict:
    from app.services.audience_map import build_audience_map, report_to_markdown

    report = build_audience_map(path, track_title=title)
    return {"report": report.model_dump(), "markdown": report_to_markdown(report)}


def _api_analyze(api_base: str, asset_id: str, token: str) -> dict:
    import httpx

    base = api_base.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.post(
        f"{base}/music/media/assets/{asset_id}/audience-map",
        headers=headers,
        timeout=300.0,
    )
    resp.raise_for_status()
    report = resp.json()
    md_resp = httpx.get(f"{base}/music/audience-profile/markdown", headers=headers, timeout=30.0)
    markdown = md_resp.json().get("markdown") if md_resp.status_code == 200 else ""
    return {"report": report, "markdown": markdown}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audience map for a track")
    parser.add_argument("--file", help="Local audio file path")
    parser.add_argument("--out", help="Write markdown report to this path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--api", help="API base URL (e.g. http://localhost:8080)")
    parser.add_argument("--asset-id", help="Media asset UUID (requires --api and --token)")
    parser.add_argument("--token", help="Auth0 bearer token for API mode")
    parser.add_argument("--title", help="Track title for reports")
    args = parser.parse_args()

    try:
        if args.api and args.asset_id:
            if not args.token:
                print("Error: --token required for API mode", file=sys.stderr)
                return 1
            result = _api_analyze(args.api, args.asset_id, args.token)
        elif args.file:
            if not os.path.isfile(args.file):
                print(f"Error: file not found: {args.file}", file=sys.stderr)
                return 1
            result = _local_analyze(args.file, args.title)
        else:
            parser.print_help()
            return 1

        if args.json:
            print(json.dumps(result["report"], indent=2))
        else:
            print(result["markdown"] or json.dumps(result["report"], indent=2))

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(result["markdown"] or json.dumps(result["report"], indent=2))
            print(f"Wrote {args.out}", file=sys.stderr)

        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
