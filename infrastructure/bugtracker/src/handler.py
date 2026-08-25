"""POST /reports — store an annotated screenshot and open a GitHub issue."""

from __future__ import annotations

import base64
import json
import os
import re
import uuid
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

PRESIGN_EXPIRES = int(os.environ.get("PRESIGN_EXPIRES", str(7 * 24 * 3600)))
MAX_IMAGE_BYTES = 6 * 1024 * 1024
GITHUB_API = "https://api.github.com"

_secret_cache: dict[str, str] | None = None


class ReportError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    extras = {item.strip() for item in os.environ.get("ALLOWED_ORIGINS", "").split(",") if item.strip()}
    if origin in extras:
        return True
    try:
        parsed = urlparse(origin)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    port = parsed.port
    scheme = parsed.scheme
    if host in {"localhost", "127.0.0.1"} and scheme in {"http", "https"}:
        return port in {None, 3000, 3030}
    if host.endswith(".localhost") and scheme in {"http", "https"}:
        return port in {None, 3000, 3030}
    if scheme != "https":
        return False
    if host in {"c0ll3ct1v3.xyz", "www.c0ll3ct1v3.xyz"}:
        return True
    return host.endswith(".c0ll3ct1v3.xyz") and host.count(".") >= 2


def cors_headers(origin: str) -> dict[str, str]:
    allow = origin if origin_allowed(origin) else "https://c0ll3ct1v3.xyz"
    return {
        "Access-Control-Allow-Origin": allow,
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Allow-Headers": "content-type",
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
    }


def response(status: int, body: Any, origin: str) -> dict[str, Any]:
    payload = body if isinstance(body, str) else json.dumps(body)
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            **cors_headers(origin),
        },
        "body": payload,
    }


def _header(event: dict[str, Any], name: str) -> str:
    headers = event.get("headers") or {}
    lower = {str(k).lower(): v for k, v in headers.items()}
    return str(lower.get(name.lower()) or "")


def _http_method(event: dict[str, Any]) -> str:
    ctx = event.get("requestContext") or {}
    http = ctx.get("http") or {}
    return str(http.get("method") or event.get("httpMethod") or "POST").upper()


def parse_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body")
    if raw is None:
        raise ReportError(400, "Missing body")
    if isinstance(raw, dict):
        return raw
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ReportError(400, "Body must be JSON") from exc
    if not isinstance(data, dict):
        raise ReportError(400, "Body must be a JSON object")
    return data


def decode_image(data_url: str) -> tuple[bytes, str]:
    if not data_url or not isinstance(data_url, str):
        raise ReportError(400, "image_data_url is required")
    match = re.match(r"^data:(image/(?:png|jpeg|jpg));base64,(.+)$", data_url, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ReportError(400, "image_data_url must be a PNG or JPEG data URL")
    content_type = match.group(1).lower()
    if content_type == "image/jpg":
        content_type = "image/jpeg"
    try:
        blob = base64.b64decode(match.group(2), validate=False)
    except Exception as exc:
        raise ReportError(400, "Invalid image encoding") from exc
    if not blob:
        raise ReportError(400, "Empty image")
    if len(blob) > MAX_IMAGE_BYTES:
        raise ReportError(413, "Screenshot is too large")
    return blob, content_type


def public_object_url(bucket: str, key: str) -> str:
    """Unsigned HTTPS URL. GitHub Camo cannot use SigV4 presigned S3 URLs (403)."""
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def report_type(value: Any) -> str:
    kind = str(value or "bug").strip().lower()
    if kind in {"feature", "feature-request", "feature_request"}:
        return "feature"
    if kind != "bug":
        raise ReportError(400, "type must be bug or feature")
    return "bug"


def issue_title(summary: str) -> str:
    text = re.sub(r"\s+", " ", summary).strip() or "Client report"
    if len(text) > 72:
        return text[:69] + "..."
    return text


def build_issue_body(
    *,
    summary: str,
    kind: str,
    page_url: str,
    viewport: dict[str, Any],
    user_agent: str,
    console_errors: list[Any],
    image_url: str,
    s3_key: str,
) -> str:
    lines = [
        f"**Type:** `{kind}`",
        "",
        "## Summary",
        summary.strip() or "(none)",
        "",
        "## Screenshot",
        f"![annotated screenshot]({image_url})",
        "",
        f"_S3 key:_ `{s3_key}` (anonymous GET on `reports/*`; objects expire after 90 days)",
        "",
        "## Context",
        f"- Page: {page_url or '(unknown)'}",
        f"- Viewport: {viewport.get('w')}×{viewport.get('h')} @ dpr {viewport.get('dpr')}",
        f"- User agent: `{user_agent or '(unknown)'}`",
        "",
        "## Console errors",
    ]
    if not console_errors:
        lines.append("_(none captured)_")
    else:
        for entry in console_errors[:25]:
            if isinstance(entry, dict):
                lines.append(f"- `{entry.get('t', '')}` {entry.get('msg', entry)}")
            else:
                lines.append(f"- {entry}")
    lines.append("")
    lines.append("_Filed by the in-app bugtracker widget (`source:client`)._")
    return "\n".join(lines)


def load_github_config(get_secret: Callable[[str], dict[str, str]] | None = None) -> dict[str, str]:
    global _secret_cache
    arn = (os.environ.get("GITHUB_SECRET_ARN") or "").strip()
    if arn:
        if _secret_cache is None:
            if get_secret:
                _secret_cache = get_secret(arn)
            else:
                import boto3

                client = boto3.client("secretsmanager")
                raw = client.get_secret_value(SecretId=arn)["SecretString"]
                _secret_cache = json.loads(raw)
        token = (_secret_cache or {}).get("token")
        owner = (_secret_cache or {}).get("owner")
        repo = (_secret_cache or {}).get("repo")
        if token and owner and repo:
            return {"token": token, "owner": owner, "repo": repo}
        raise ReportError(500, "GitHub secret is missing token, owner, or repo")
    token = os.environ.get("GITHUB_TOKEN") or ""
    owner = os.environ.get("GITHUB_OWNER") or ""
    repo = os.environ.get("GITHUB_REPO") or ""
    if token and owner and repo:
        return {"token": token, "owner": owner, "repo": repo}
    raise ReportError(500, "GitHub credentials are not configured")


def create_github_issue(
    *,
    config: dict[str, str],
    title: str,
    body: str,
    labels: list[str],
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    url = f"{GITHUB_API}/repos/{config['owner']}/{config['repo']}/issues"
    payload = json.dumps({"title": title, "body": body, "labels": labels}).encode("utf-8")
    req = Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {config['token']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "c0ll3ct1v3-bugtracker",
        },
    )
    try:
        with opener(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code == 422 and labels:
            return create_github_issue(
                config=config, title=title, body=body, labels=[], opener=opener
            )
        raise ReportError(502, f"GitHub issue create failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise ReportError(502, f"GitHub unreachable: {exc.reason}") from exc


def process_report(
    body: dict[str, Any],
    *,
    s3: Any,
    bucket: str,
    github_config: dict[str, str],
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    summary = str(body.get("summary") or "").strip()
    if not summary:
        raise ReportError(400, "summary is required")
    kind = report_type(body.get("type"))
    blob, content_type = decode_image(str(body.get("image_data_url") or ""))
    ext = "jpg" if content_type == "image/jpeg" else "png"
    key = f"reports/{uuid.uuid4()}.{ext}"
    s3.put_object(Bucket=bucket, Key=key, Body=blob, ContentType=content_type)
    image_url = public_object_url(bucket, key)
    viewport = body.get("viewport") if isinstance(body.get("viewport"), dict) else {}
    console_errors = body.get("console_errors") if isinstance(body.get("console_errors"), list) else []
    labels = ["source:client", "type:feature-request" if kind == "feature" else "type:bug"]
    issue = create_github_issue(
        config=github_config,
        title=issue_title(summary),
        body=build_issue_body(
            summary=summary,
            kind=kind,
            page_url=str(body.get("page_url") or ""),
            viewport=viewport,
            user_agent=str(body.get("user_agent") or ""),
            console_errors=console_errors,
            image_url=image_url,
            s3_key=key,
        ),
        labels=labels,
        opener=opener,
    )
    return {
        "ok": True,
        "issue_url": issue.get("html_url"),
        "issue_number": issue.get("number"),
        "s3_key": key,
    }


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    origin = _header(event, "origin")
    try:
        if _http_method(event) == "OPTIONS":
            return {
                "statusCode": 204,
                "headers": cors_headers(origin),
                "body": "",
            }
        if _http_method(event) != "POST":
            raise ReportError(405, "Method not allowed")
        body = parse_body(event)
        bucket = os.environ.get("REPORTS_BUCKET") or ""
        if not bucket:
            raise ReportError(500, "REPORTS_BUCKET is not set")
        import boto3

        s3 = boto3.client("s3")
        result = process_report(
            body,
            s3=s3,
            bucket=bucket,
            github_config=load_github_config(),
        )
        return response(200, result, origin)
    except ReportError as exc:
        return response(exc.status, {"ok": False, "error": exc.message}, origin)
    except Exception:
        return response(500, {"ok": False, "error": "Unexpected error"}, origin)
