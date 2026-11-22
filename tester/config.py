from __future__ import annotations

import json
import os
from urllib.parse import urlparse

DEFAULT_TARGET_TOKEN = os.getenv("TARGET_API_TOKEN", "")
TARGET_ACTOR = os.getenv("TARGET_ACTOR", "team21-tester")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("TARGET_REQUEST_TIMEOUT_SECONDS", "20"))
OWN_SYSTEM_URL = os.getenv(
    "TEAM21_SYSTEM_URL",
    "https://team21-cra-reporting-service.onrender.com",
).rstrip("/")


def _token_map() -> dict[str, str]:
    raw = os.getenv("TARGET_TOKENS_JSON", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in data.items()}


def token_for_target(target_url: str) -> str:
    mapping = _token_map()
    parsed = urlparse(target_url)
    host = parsed.netloc
    normalized = target_url.rstrip("/")

    # Accept either a full base URL key or a hostname key.
    if normalized in mapping:
        return mapping[normalized]
    if host in mapping:
        return mapping[host]
    return DEFAULT_TARGET_TOKEN
