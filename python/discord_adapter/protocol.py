"""
Versioned JSON Lines protocol for communication with Rust.
"""

from __future__ import annotations

import json

from dataclasses import dataclass
from typing import Any


PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class EngineResponse:
    protocol_version: int
    request_id: str
    ok: bool
    payload: dict[str, Any] | None
    error: dict[str, str] | None


def encode_request(
    request_id: str,
    operation: str,
    payload: dict[str, Any] | None = None,
) -> str:

    if not request_id:
        raise ValueError("request_id must not be empty")

    if not operation:
        raise ValueError("operation must not be empty")

    message = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "kind": "request",
        "operation": operation,
        "payload": payload or {},
    }

    return json.dumps(
        message,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def decode_response(line: str) -> EngineResponse:

    raw = json.loads(line)

    if not isinstance(raw, dict):
        raise ValueError(
            "Engine response must be a JSON object"
        )

    version = raw.get("protocol_version")
    request_id = raw.get("request_id")
    ok = raw.get("ok")

    if version != PROTOCOL_VERSION:
        raise ValueError(
            f"Unsupported protocol version: {version!r}"
        )

    if not isinstance(request_id, str):
        raise ValueError(
            "Missing request_id"
        )

    if not isinstance(ok, bool):
        raise ValueError(
            "Missing boolean ok field"
        )

    payload = raw.get("payload")
    error = raw.get("error")

    if payload is not None and not isinstance(payload, dict):
        raise ValueError(
            "Response payload must be an object"
        )

    if error is not None and not isinstance(error, dict):
        raise ValueError(
            "Response error must be an object"
        )

    return EngineResponse(
        protocol_version=version,
        request_id=request_id,
        ok=ok,
        payload=payload,
        error=error,
    )
