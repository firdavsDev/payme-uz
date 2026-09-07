"""JSON-RPC transport: one place that knows how to talk to Payme."""

from __future__ import annotations

import itertools
import logging
from typing import Any

from aiohttp import ClientSession, ClientTimeout, TCPConnector

from .errors import PaymeTransportError, from_error_object
from .redaction import redact
from .retry import NO_RETRY, RetryPolicy

logger = logging.getLogger(__name__)

# Payme is one host, so a small pool is plenty; keepalive avoids a TLS
# handshake per call, which dominates the cost of a request.
DEFAULT_POOL_LIMIT = 100
DEFAULT_POOL_LIMIT_PER_HOST = 20
DNS_CACHE_SECONDS = 300


class JsonRpcTransport:
    """Sends JSON-RPC calls and turns error objects into exceptions.

    The session is created on first use, so constructing a client outside a
    running event loop is safe. A session passed in belongs to the caller and
    is never closed here.
    """

    def __init__(
        self,
        url: str,
        *,
        session: ClientSession | None = None,
        timeout: float = 30.0,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.retry_policy = retry_policy or RetryPolicy()
        self._session = session
        self._owns_session = session is None
        self._request_ids = itertools.count(1)

    @property
    def session(self) -> ClientSession | None:
        """The live session, or ``None`` before the first request."""
        return self._session

    def _ensure_session(self) -> ClientSession:
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                timeout=ClientTimeout(
                    total=self.timeout, connect=min(5.0, self.timeout)
                ),
                connector=TCPConnector(
                    limit=DEFAULT_POOL_LIMIT,
                    limit_per_host=DEFAULT_POOL_LIMIT_PER_HOST,
                    ttl_dns_cache=DNS_CACHE_SECONDS,
                    enable_cleanup_closed=True,
                ),
            )
            self._owns_session = True
        return self._session

    async def call(
        self,
        method: str,
        params: dict[str, Any],
        headers: dict[str, str],
        *,
        retry: bool = False,
    ) -> dict[str, Any]:
        """Send one call and return its ``result``.

        Raises :class:`~payme.errors.PaymeAPIError` for a JSON-RPC error and
        :class:`~payme.errors.PaymeTransportError` when no usable response
        arrived. ``retry`` must stay false for anything that moves money.
        """
        payload = {"id": next(self._request_ids), "method": method, "params": params}
        policy = self.retry_policy if retry else NO_RETRY
        session = self._ensure_session()

        attempt = 0
        while True:
            attempt += 1
            try:
                result = await self._send(session, payload, headers)
            except Exception as exc:
                if policy.should_retry(exc, attempt):
                    logger.warning(
                        "[Payme API] %s failed (attempt %s/%s): %s; retrying",
                        method,
                        attempt,
                        policy.attempts,
                        exc,
                    )
                    await policy.sleep(attempt)
                    continue
                raise
            return result

    async def _send(
        self,
        session: ClientSession,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        method = payload["method"]
        async with session.post(
            url=self.url, json=payload, headers=headers
        ) as response:
            try:
                body = await response.json(content_type=None)
            except Exception as e:
                raise PaymeTransportError(
                    f"Payme returned a non-JSON response ({response.status})",
                    method=method,
                ) from e

            if response.status != 200:
                logger.error(
                    "[Payme API] %s non-200 response (%s): %s",
                    method,
                    response.status,
                    redact(body),
                )

            if not isinstance(body, dict):
                raise PaymeTransportError(
                    f"Unexpected JSON-RPC payload of type {type(body).__name__}",
                    method=method,
                )

            logger.info("[Payme API] %s response: %s", method, redact(body))

            if body.get("error"):
                raise from_error_object(body["error"], method=method)
            return body.get("result", {})

    async def close(self) -> None:
        """Close the session, unless it was handed in by the caller."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> JsonRpcTransport:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
