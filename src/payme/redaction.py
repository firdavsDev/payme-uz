"""Masking for values that must never reach a log file."""

from __future__ import annotations

from typing import Any

# A card token is a bearer credential: with the cashbox key it can charge the
# card. Card number and expiry are card data in their own right.
SECRET_KEYS = frozenset({"token", "number", "expire"})


def mask(secret: str) -> str:
    """Keep just enough of a secret to correlate two log lines."""
    if len(secret) <= 8:
        return "***"
    return f"{secret[:8]}...({len(secret)} chars)"


def redact(value: Any) -> Any:
    """Copy a payload with every secret value masked."""
    if isinstance(value, dict):
        return {
            k: (mask(v) if k in SECRET_KEYS and isinstance(v, str) else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value
