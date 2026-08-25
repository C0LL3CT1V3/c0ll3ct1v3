import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from urllib.error import HTTPError

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import handler  # noqa: E402


TINY_JPEG = (
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBwgHBgkIBwgKCgkLDRYPDQwMDRsUFRAWIB0iIiAdHx8kKDQsJCYxJx8fLT0tMTU3Ojo6Iys/RD84QzQ5OjcBCgoKDQwNGg8PGjclHyU3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3N//AABEIAAEAAQMBEQACEQEDEQH/xAAXAAADAQAAAAAAAAAAAAAAAAABAgME/8QAFhABAQEAAAAAAAAAAAAAAAAAABEB/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAGfP//Z"
)


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = {"bucket": Bucket, "body": Body, "content_type": ContentType}

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        return f"https://s3.example/{Params['Key']}?expires={ExpiresIn}"


class OriginTests(unittest.TestCase):
    def test_localhost_and_prod(self):
        self.assertTrue(handler.origin_allowed("http://localhost:3030"))
        self.assertTrue(handler.origin_allowed("http://127.0.0.1:3030"))
        self.assertTrue(handler.origin_allowed("https://c0ll3ct1v3.xyz"))
        self.assertTrue(handler.origin_allowed("https://demo.c0ll3ct1v3.xyz"))
        self.assertTrue(handler.origin_allowed("http://demo.localhost:3030"))
        self.assertFalse(handler.origin_allowed("https://evil.example"))
        self.assertFalse(handler.origin_allowed("http://c0ll3ct1v3.xyz"))

    def test_allowed_origins_env(self):
        os.environ["ALLOWED_ORIGINS"] = "https://extra.example"
        try:
            self.assertTrue(handler.origin_allowed("https://extra.example"))
        finally:
            os.environ.pop("ALLOWED_ORIGINS", None)


class ProcessReportTests(unittest.TestCase):
    def setUp(self):
        handler._secret_cache = None
        self.s3 = FakeS3()
        self.config = {"token": "ghs_test", "owner": "acme", "repo": "c0ll3ct1v3"}

    def test_creates_issue_and_uploads(self):
        captured = {}

        def opener(req, timeout=15):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))
            buf = io.BytesIO(
                json.dumps({"html_url": "https://github.com/acme/c0ll3ct1v3/issues/9", "number": 9}).encode()
            )
            ctx = MagicMock()
            ctx.read.return_value = buf.getvalue()
            ctx.__enter__.return_value = ctx
            ctx.__exit__.return_value = False
            return ctx

        result = handler.process_report(
            {
                "image_data_url": TINY_JPEG,
                "summary": "Button does nothing on vault",
                "type": "bug",
                "page_url": "http://localhost:3030/portal/vault",
                "viewport": {"w": 1440, "h": 900, "dpr": 2},
                "user_agent": "Mozilla/5.0",
                "console_errors": [{"t": 1, "msg": "boom"}],
            },
            s3=self.s3,
            bucket="reports-bucket",
            github_config=self.config,
            opener=opener,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["issue_url"], "https://github.com/acme/c0ll3ct1v3/issues/9")
        self.assertTrue(result["s3_key"].startswith("reports/"))
        self.assertEqual(len(self.s3.objects), 1)
        self.assertIn("type:bug", captured["body"]["labels"])
        self.assertIn("source:client", captured["body"]["labels"])
        self.assertIn("Button does nothing", captured["body"]["title"])
        self.assertIn("boom", captured["body"]["body"])
        self.assertIn("reports-bucket.s3.us-east-2.amazonaws.com/reports/", captured["body"]["body"])
        self.assertNotIn("X-Amz-Signature", captured["body"]["body"])

    def test_public_object_url(self):
        url = handler.public_object_url("my-bucket", "reports/abc.jpg")
        self.assertEqual(url, "https://my-bucket.s3.us-east-2.amazonaws.com/reports/abc.jpg")

    def test_rejects_missing_summary(self):
        with self.assertRaises(handler.ReportError) as ctx:
            handler.process_report(
                {"image_data_url": TINY_JPEG, "type": "bug"},
                s3=self.s3,
                bucket="b",
                github_config=self.config,
            )
        self.assertEqual(ctx.exception.status, 400)

    def test_options_and_post_wrapper(self):
        event = {
            "headers": {"origin": "http://localhost:3030"},
            "requestContext": {"http": {"method": "OPTIONS"}},
        }
        out = handler.lambda_handler(event, None)
        self.assertEqual(out["statusCode"], 204)
        self.assertEqual(out["headers"]["Access-Control-Allow-Origin"], "http://localhost:3030")

    def test_github_config_from_secret(self):
        os.environ["GITHUB_SECRET_ARN"] = "arn:aws:secretsmanager:us-east-2:1:secret:x"
        try:
            cfg = handler.load_github_config(
                get_secret=lambda _arn: {"token": "t", "owner": "o", "repo": "r"}
            )
            self.assertEqual(cfg["owner"], "o")
        finally:
            os.environ.pop("GITHUB_SECRET_ARN", None)
            handler._secret_cache = None

    def test_retries_without_labels_on_422(self):
        calls = {"n": 0}

        def opener(req, timeout=15):
            calls["n"] += 1
            payload = json.loads(req.data.decode("utf-8"))
            if payload.get("labels"):
                raise HTTPError(req.full_url, 422, "Unprocessable", hdrs=None, fp=io.BytesIO(b"{}"))
            ctx = MagicMock()
            ctx.read.return_value = json.dumps({"html_url": "https://github.com/x/y/issues/1", "number": 1}).encode()
            ctx.__enter__.return_value = ctx
            ctx.__exit__.return_value = False
            return ctx

        result = handler.process_report(
            {"image_data_url": TINY_JPEG, "summary": "x", "type": "feature"},
            s3=self.s3,
            bucket="b",
            github_config=self.config,
            opener=opener,
        )
        self.assertEqual(calls["n"], 2)
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
