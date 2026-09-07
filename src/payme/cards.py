"""Card methods of the Subscribe API.

These authenticate with the cashbox id alone and never move money, so the
read-only ones are safe to retry.
"""

from __future__ import annotations

from typing import Any

from .config import PaymeConfig
from .transport import JsonRpcTransport
from .validation import normalize_card


class CardsAPI:
    """``cards.*`` methods, reachable as ``client.cards``."""

    def __init__(self, transport: JsonRpcTransport, config: PaymeConfig) -> None:
        self._transport = transport
        self._config = config

    async def create(
        self, number: str, expire: str, *, save: bool = False
    ) -> dict[str, Any]:
        """Tokenize a card. ``number`` may contain spaces, ``expire`` may be MM/YY."""
        number, expire = normalize_card(number, expire)
        return await self._transport.call(
            "cards.create",
            {"card": {"number": number, "expire": expire}, "save": save},
            self._config.card_auth,
        )

    async def get_verify_code(self, token: str) -> dict[str, Any]:
        """Ask Payme to SMS a verification code to the cardholder."""
        return await self._transport.call(
            "cards.get_verify_code", {"token": token}, self._config.card_auth
        )

    async def verify(self, token: str, code: str) -> dict[str, Any]:
        """Confirm the card with the code the cardholder received."""
        return await self._transport.call(
            "cards.verify",
            {"token": token, "code": str(code)},
            self._config.card_auth,
        )

    async def check(self, token: str) -> dict[str, Any]:
        """Check that a token is still usable."""
        return await self._transport.call(
            "cards.check", {"token": token}, self._config.card_auth, retry=True
        )

    async def remove(self, token: str) -> dict[str, Any]:
        """Revoke a token. It stops working immediately."""
        return await self._transport.call(
            "cards.remove", {"token": token}, self._config.card_auth, retry=True
        )
