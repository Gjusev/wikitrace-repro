"""Z.ai owner rules: pinned endpoint/model, key gating, billing STOP.

All tests use injectable openers -- no network access, ever.
"""

import os
import unittest
from unittest.mock import patch

import urllib.error

from wikitrace_repro import zai


def _fake_response(body):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return body.encode("utf-8")

    return _Resp()


class _Opener:
    """Records the request and returns a canned response."""

    def __init__(self, body=None, error=None):
        self.body = body or '{"choices": [{"message": {"content": "OK"}}]}'
        self.error = error
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return _fake_response(self.body)


class TestPinnedConfig(unittest.TestCase):
    def test_model_is_pinned(self):
        self.assertEqual(zai.MODEL, "glm-5.3-flash")

    def test_base_url_is_zai_coding_plan(self):
        self.assertEqual(zai.BASE_URL, "https://api.z.ai/api/coding/paas/v4")

    def test_key_env_var_name(self):
        self.assertEqual(zai.KEY_ENV, "WIKITRACE_ZAI_KEY")

    def test_other_model_refused(self):
        with self.assertRaises(zai.ZaiConfigError):
            zai.chat([{"role": "user", "content": "hi"}], model="gpt-4o",
                     opener=_Opener())


class TestKeyGating(unittest.TestCase):
    def test_missing_key_raises_config_error(self):
        env = {k: v for k, v in os.environ.items() if k != zai.KEY_ENV}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(zai.ZaiConfigError):
                zai.resolve_key()

    def test_key_from_env(self):
        with patch.dict(os.environ, {zai.KEY_ENV: "sk-test"}):
            self.assertEqual(zai.resolve_key(), "sk-test")


class TestChat(unittest.TestCase):
    def test_success_call_sets_auth_header(self):
        opener = _Opener()
        out = zai.chat([{"role": "user", "content": "hi"}], key="sk-test",
                       opener=opener)
        self.assertEqual(out, "OK")
        self.assertEqual(opener.requests[0].get_header("Authorization"),
                         "Bearer sk-test")

    def test_billing_error_stops(self):
        for code in (401, 402, 403, 429):
            opener = _Opener(error=urllib.error.HTTPError(
                zai.BASE_URL, code, "nope", None, None))
            with self.assertRaises(zai.ZaiBillingStop) as ctx:
                zai.chat([{"role": "user", "content": "hi"}], key="sk-test",
                         opener=opener)
            ctx.exception.__cause__.close()  # close the HTTPError's temp file

    def test_non_billing_http_error_not_masked(self):
        opener = _Opener(error=urllib.error.HTTPError(
            zai.BASE_URL, 500, "boom", None, None))
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            zai.chat([{"role": "user", "content": "hi"}], key="sk-test",
                     opener=opener)
        ctx.exception.close()  # release the HTTPError's temp file


if __name__ == "__main__":
    unittest.main()
