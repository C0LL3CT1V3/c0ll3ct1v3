#!/usr/bin/env python3
"""
CLI driver for c0ll3ct1v3 manager EPK chat-edit flow.

Uses agent key auth (Bearer + X-Tenant-Slug) or Auth0 token.

Examples:
  export C0LL3CT1V3_API_URL=http://localhost:8080
  export C0LL3CT1V3_AGENT_KEY=dev-agent-local
  export C0LL3CT1V3_TENANT_SLUG=phillipjames

  python3 scripts/manager_epk.py thread create --mode epk_builder
  python3 scripts/manager_epk.py iterate "dark outlaw country EPK"
  python3 scripts/manager_epk.py chat "What should I upload next?"
  python3 scripts/manager_epk.py draft
  python3 scripts/manager_epk.py annotate --iteration-id UUID --note "Bigger headline" --component hero
  python3 scripts/manager_epk.py refine --iteration-id UUID
  python3 scripts/manager_epk.py accept --iteration-id UUID
  python3 scripts/manager_epk.py publish
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_STATE_PATH = _REPO_ROOT / "scripts" / ".state" / "manager-state.json"


def _load_state() -> dict:
    if _STATE_PATH.is_file():
        try:
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _save_state(data: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _api_base() -> str:
    return (
        os.environ.get("C0LL3CT1V3_API_URL")
        or os.environ.get("REACT_APP_API_URL")
        or "http://localhost:8080"
    ).rstrip("/")


def _tenant_slug() -> str:
    slug = (
        os.environ.get("C0LL3CT1V3_TENANT_SLUG")
        or os.environ.get("DEFAULT_MEDIA_TENANT_SLUG")
        or "phillipjames"
    ).strip().lower()
    if not slug:
        print("Error: set C0LL3CT1V3_TENANT_SLUG", file=sys.stderr)
        sys.exit(1)
    return slug


def _headers() -> dict[str, str]:
    agent_key = (os.environ.get("C0LL3CT1V3_AGENT_KEY") or "").strip()
    token = (os.environ.get("C0LL3CT1V3_TOKEN") or os.environ.get("TOKEN") or "").strip()
    if agent_key:
        return {
            "Authorization": f"Bearer {agent_key}",
            "X-Tenant-Slug": _tenant_slug(),
            "Content-Type": "application/json",
        }
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print(
        "Error: set C0LL3CT1V3_AGENT_KEY (automation) or C0LL3CT1V3_TOKEN (Auth0)",
        file=sys.stderr,
    )
    sys.exit(1)


def _request(method: str, path: str, *, json_body: dict | None = None) -> dict:
    import json as json_mod
    import urllib.error
    import urllib.request

    url = f"{_api_base()}{path}"
    data = None
    if json_body is not None:
        data = json_mod.dumps(json_body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        try:
            detail = json_mod.loads(detail).get("detail", detail)
        except Exception:  # noqa: BLE001
            pass
        print(f"Error {exc.code}: {detail}", file=sys.stderr)
        sys.exit(1)
    if not raw:
        return {}
    return json_mod.loads(raw)


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2))


def cmd_thread_create(args: argparse.Namespace) -> int:
    data = _request("POST", "/manager/threads", json_body={"mode": args.mode})
    state = _load_state()
    state["thread_id"] = data["id"]
    state["thread_mode"] = data["mode"]
    _save_state(state)
    _print_json(data)
    return 0


def cmd_thread_show(_args: argparse.Namespace) -> int:
    state = _load_state()
    thread_id = state.get("thread_id")
    if not thread_id:
        print("No saved thread_id — run: manager_epk.py thread create", file=sys.stderr)
        return 1
    _print_json(_request("GET", f"/manager/threads/{thread_id}"))
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    state = _load_state()
    body = {"message": args.message, "thread_id": state.get("thread_id")}
    data = _request("POST", "/manager/chat", json_body=body)
    state["thread_id"] = data["thread_id"]
    _save_state(state)
    print(data.get("reply", ""))
    return 0


def cmd_iterate(args: argparse.Namespace) -> int:
    state = _load_state()
    if args.new_thread:
        thread = _request("POST", "/manager/threads", json_body={"mode": "epk_builder"})
        state["thread_id"] = thread["id"]
    body = {"prompt": args.prompt, "thread_id": state.get("thread_id")}
    data = _request("POST", "/manager/epk/iterate", json_body=body)
    state["thread_id"] = data["thread_id"]
    state["iteration_id"] = data["iteration_id"]
    _save_state(state)
    summary = data.get("reasoning_summary") or "EPK draft updated."
    print(summary)
    if args.json:
        _print_json(data)
    return 0


def cmd_draft(_args: argparse.Namespace) -> int:
    _print_json(_request("GET", "/manager/epk/draft"))
    return 0


def cmd_components(_args: argparse.Namespace) -> int:
    _print_json(_request("GET", "/manager/epk/component-map"))
    return 0


def cmd_annotate(args: argparse.Namespace) -> int:
    iteration_id = args.iteration_id or _load_state().get("iteration_id")
    if not iteration_id:
        print("Error: --iteration-id required (or run iterate first)", file=sys.stderr)
        return 1
    annotation = {"note": args.note, "component_ids": args.component or []}
    if args.component:
        annotation["component_ids"] = args.component
    body = {"annotations": [annotation]}
    _print_json(_request("POST", f"/manager/epk/iterations/{iteration_id}/annotate", json_body=body))
    return 0


def cmd_refine(args: argparse.Namespace) -> int:
    iteration_id = args.iteration_id or _load_state().get("iteration_id")
    if not iteration_id:
        print("Error: --iteration-id required", file=sys.stderr)
        return 1
    data = _request("POST", f"/manager/epk/iterations/{iteration_id}/refine")
    state = _load_state()
    state["iteration_id"] = data["iteration_id"]
    _save_state(state)
    print(data.get("reasoning_summary") or "Refined EPK draft.")
    if args.json:
        _print_json(data)
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    iteration_id = args.iteration_id or _load_state().get("iteration_id")
    if not iteration_id:
        print("Error: --iteration-id required", file=sys.stderr)
        return 1
    body = {"consent_for_training": args.consent}
    _print_json(_request("POST", f"/manager/epk/iterations/{iteration_id}/accept", json_body=body))
    return 0


def cmd_publish(_args: argparse.Namespace) -> int:
    _print_json(_request("POST", "/manager/epk/draft/publish"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="c0ll3ct1v3 manager EPK CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    thread = sub.add_parser("thread", help="Thread helpers")
    thread_sub = thread.add_subparsers(dest="thread_cmd", required=True)
    t_create = thread_sub.add_parser("create", help="Create manager thread")
    t_create.add_argument("--mode", default="epk_builder", choices=["general", "epk_builder"])
    t_create.set_defaults(func=cmd_thread_create)
    t_show = thread_sub.add_parser("show", help="Show saved thread + messages")
    t_show.set_defaults(func=cmd_thread_show)

    chat = sub.add_parser("chat", help="General manager chat")
    chat.add_argument("message")
    chat.set_defaults(func=cmd_chat)

    iterate = sub.add_parser("iterate", help="EPK chat-edit: apply prompt to draft")
    iterate.add_argument("prompt")
    iterate.add_argument("--new-thread", action="store_true", help="Start fresh epk_builder thread")
    iterate.add_argument("--json", action="store_true")
    iterate.set_defaults(func=cmd_iterate)

    draft = sub.add_parser("draft", help="GET current EPK draft preview payload")
    draft.set_defaults(func=cmd_draft)

    components = sub.add_parser("components", help="GET annotatable component map")
    components.set_defaults(func=cmd_components)

    annotate = sub.add_parser("annotate", help="Attach text notes to components")
    annotate.add_argument("--iteration-id")
    annotate.add_argument("--note", required=True)
    annotate.add_argument("--component", action="append", help="Component id e.g. hero, bio-main")
    annotate.set_defaults(func=cmd_annotate)

    refine = sub.add_parser("refine", help="Refine draft from annotations")
    refine.add_argument("--iteration-id")
    refine.add_argument("--json", action="store_true")
    refine.set_defaults(func=cmd_refine)

    accept = sub.add_parser("accept", help="Accept current iteration")
    accept.add_argument("--iteration-id")
    accept.add_argument("--consent", action="store_true", help="Allow training contribution")
    accept.set_defaults(func=cmd_accept)

    publish = sub.add_parser("publish", help="Publish epk_draft to live epk_config")
    publish.set_defaults(func=cmd_publish)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
