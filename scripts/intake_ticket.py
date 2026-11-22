"""Submit a researcher-supplied CRA ticket through Team 21's own JSON-file intake."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx


DEFAULT_BASE_URL = "https://team21-cra-reporting-service.onrender.com"


def submit_intake(
    payload: dict,
    *,
    base_url: str,
    api_token: str,
    actor: str,
    client: httpx.Client,
) -> dict:
    """Submit one ticket; omit reporter details from command output and errors."""
    if not api_token:
        raise ValueError("Set CRA_API_TOKEN before submitting a ticket.")
    if not actor.strip():
        raise ValueError("X-Actor must not be blank.")
    if not isinstance(payload, dict):
        raise ValueError("The intake file must be a JSON object.")

    response = client.post(
        f"{base_url.rstrip('/')}/tickets",
        headers={
            "Authorization": f"Bearer {api_token}",
            "X-Actor": actor.strip(),
        },
        json=payload,
    )
    if response.status_code != 201:
        # The response may contain sensitive information. Do not echo its body.
        raise RuntimeError(f"Ticket intake failed with HTTP {response.status_code}.")
    data = response.json()
    return {
        "id": data["id"],
        "state": data["state"],
        "received_at": data["received_at"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Intake a researcher's JSON vulnerability report into the CRA ticket service."
    )
    parser.add_argument("json_file", type=Path, help="JSON file conforming to POST /tickets")
    parser.add_argument(
        "--base-url",
        default=os.getenv("CRA_BASE_URL", DEFAULT_BASE_URL),
        help="Team 21 system base URL (defaults to the registered evaluation deployment)",
    )
    parser.add_argument(
        "--actor",
        default=os.getenv("CRA_ACTOR", "team21-cli-intake"),
        help="Person or client identifier for the append-only audit log",
    )
    args = parser.parse_args()
    try:
        payload = json.loads(args.json_file.read_text(encoding="utf-8"))
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            created = submit_intake(
                payload,
                base_url=args.base_url,
                api_token=os.getenv("CRA_API_TOKEN", ""),
                actor=args.actor,
                client=client,
            )
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, httpx.HTTPError) as exc:
        parser.exit(1, f"Intake failed: {exc}\n")
    print(json.dumps(created, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
