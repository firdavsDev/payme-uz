"""Shared fakes. No test in this suite touches the network."""

from __future__ import annotations

from typing import Any

import pytest


class FakeResponse:
    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self._body = body

    async def json(self, content_type: str | None = "application/json") -> Any:
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class _ResponseContext:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    async def __aenter__(self) -> FakeResponse:
        return self._response

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


class FakeSession:
    """Scripted stand-in for aiohttp.ClientSession.

    Each scripted item is either a body dict, a (status, body) pair, or an
    exception to raise from ``post`` - which is how a connection failure
    reaches the transport.
    """

    def __init__(self, *script: Any) -> None:
        self._script = list(script)
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    def post(self, url: str, json: dict[str, Any], headers: dict[str, str]):
        self.calls.append({"url": url, "json": json, "headers": headers})
        item = self._script.pop(0) if self._script else {"result": {}}
        if isinstance(item, Exception):
            raise item
        status, body = item if isinstance(item, tuple) else (200, item)
        return _ResponseContext(FakeResponse(status, body))

    async def close(self) -> None:
        self.closed = True

    @property
    def last_payload(self) -> dict[str, Any]:
        return self.calls[-1]["json"]

    @property
    def last_headers(self) -> dict[str, str]:
        return self.calls[-1]["headers"]


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()


@pytest.fixture(autouse=True)
def payme_env(monkeypatch):
    """Config is read per client, so tests can set it freely."""
    monkeypatch.setenv("PAYME_ENV", "false")
    monkeypatch.setenv("PAYME_TOKEN", "test-token")
    monkeypatch.setenv("PAYME_SECRET_KEY", "test-secret")
    monkeypatch.setenv("PAYME_ACCOUNT_KEY_1", "order_id")
    monkeypatch.setenv("PAYME_ACCOUNT_KEY_2", "order_type")
