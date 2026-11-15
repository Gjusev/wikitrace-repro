"""Real-model access -- Z.ai Coding Plan ONLY, glm-5.3-flash ONLY.

Owner rules baked in (do not relax them):

- All LLM calls go to ``https://api.z.ai/api/coding/paas/v4`` with model
  ``glm-5.3-flash``. No other provider, no other model, no fallback.
- The key comes from the ``WIKITRACE_ZAI_KEY`` environment variable.
- On a billing/auth/endpoint error (401/402/403/429): STOP and report.
  Never switch providers or models to "get it working" -- the plan is a
  flat subscription.
- Real runs are owner-approval-gated; nothing in the test suite or the
  offline bench calls this module.

Network imports stay lazy inside the function that needs them so the
offline suite never touches the network.
"""

from __future__ import annotations

BASE_URL = "https://api.z.ai/api/coding/paas/v4"
MODEL = "glm-5.3-flash"
KEY_ENV = "WIKITRACE_ZAI_KEY"

_BILLING_CODES = frozenset({401, 402, 403, 429})


class ZaiConfigError(RuntimeError):
    """Missing or wrong Z.ai configuration."""


class ZaiBillingStop(RuntimeError):
    """Billing/endpoint error -- STOP per owner rules. Do not fall back."""


def resolve_key(key: str | None = None) -> str:
    if key:
        return key
    import os

    key = os.environ.get(KEY_ENV)
    if not key:
        raise ZaiConfigError(
            f"set {KEY_ENV} to your Z.ai Coding Plan key "
            f"({BASE_URL}, model {MODEL})"
        )
    return key


def chat(messages, *, key: str | None = None, base_url: str = BASE_URL,
         model: str = MODEL, timeout: int = 120, opener=None) -> str:
    """One chat completion against the Z.ai Coding Plan endpoint.

    ``opener`` is injectable for offline tests; defaults to
    ``urllib.request.urlopen``.
    """
    if model != MODEL:
        raise ZaiConfigError(
            f"model is pinned to {MODEL} by owner rules; refusing {model!r}"
        )
    import json
    import urllib.error
    import urllib.request

    opener = opener or urllib.request.urlopen
    resolved_key = resolve_key(key)
    payload = json.dumps({"model": model, "messages": list(messages)}).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {resolved_key}",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code in _BILLING_CODES:
            raise ZaiBillingStop(
                f"HTTP {exc.code} from the Z.ai coding endpoint -- STOP and report; "
                "do NOT fall back to another provider or model"
            ) from exc
        raise
    data = json.loads(body)
    return data["choices"][0]["message"]["content"]


def smoke(prompt: str = "Reply with exactly: OK") -> str:
    """Minimal real-model probe. Owner-approval-gated; costs plan quota."""
    return chat([{"role": "user", "content": prompt}])
