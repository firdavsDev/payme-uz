"""The client callers reach for: configuration plus the two method groups."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from aiohttp import ClientSession

from .cards import CardsAPI
from .checkout import build_checkout_link
from .config import PaymeConfig
from .receipts import ReceiptsAPI
from .retry import RetryPolicy
from .transport import JsonRpcTransport

logger = logging.getLogger(__name__)


class PaymeAPIClient:
    """Async client for the Payme Subscribe API.

    Grouped by protocol namespace::

        async with PaymeAPIClient() as client:
            card = await client.cards.create("8600 0691 9540 6311", "10/27")
            receipt = await client.receipts.create(order_id="42", amount=100_000)

    Errors arrive as exceptions from :mod:`payme.errors`, never as return
    values. Every setting can come from the environment, from a
    :class:`~payme.config.PaymeConfig`, or from keyword arguments here.
    """

    def __init__(
        self,
        session: ClientSession | None = None,
        *,
        config: PaymeConfig | None = None,
        token: str | None = None,
        secret_key: str | None = None,
        account_key: str | None = None,
        account_type_key: str | None = None,
        production: bool | None = None,
        timeout: float | None = None,
        retry_policy: RetryPolicy | None = None,
        transport: JsonRpcTransport | None = None,
    ) -> None:
        self.config = config or PaymeConfig.from_env(
            token=token,
            secret_key=secret_key,
            account_key=account_key,
            account_type_key=account_type_key,
            production=production,
            timeout=timeout,
        )
        missing = self.config.missing()
        if missing:
            logger.warning(
                "[Payme API] Missing configuration: %s. "
                "Calls that need it will raise PaymeConfigError.",
                ", ".join(missing),
            )

        self.transport = transport or JsonRpcTransport(
            self.config.api_url,
            session=session,
            timeout=self.config.timeout,
            retry_policy=retry_policy,
        )
        self.cards = CardsAPI(self.transport, self.config)
        self.receipts = ReceiptsAPI(self.transport, self.config)

    @property
    def url(self) -> str:
        """The API endpoint in use."""
        return self.config.api_url

    @property
    def session(self) -> ClientSession | None:
        """The underlying session, or ``None`` before the first request."""
        return self.transport.session

    def checkout_link(
        self,
        *,
        order_id: str,
        amount: Decimal | int | str,
        return_url: str,
        order_type: str | None = None,
    ) -> str:
        """Build a hosted-checkout URL. No network call, so this is not async."""
        return build_checkout_link(
            self.config,
            order_id=order_id,
            amount=amount,
            return_url=return_url,
            order_type=order_type,
        )

    # Flat aliases, kept so existing call sites keep working. Each one is a
    # single delegation; the behaviour lives in the namespace classes.

    async def create_card(
        self, card_number: str, expire: str, save: bool = False
    ) -> dict[str, Any]:
        return await self.cards.create(card_number, expire, save=save)

    async def get_card_verify_code(self, token: str) -> dict[str, Any]:
        return await self.cards.get_verify_code(token)

    async def verify_card(self, code: str, token: str) -> dict[str, Any]:
        return await self.cards.verify(token, code)

    async def check_card(self, token: str) -> dict[str, Any]:
        return await self.cards.check(token)

    async def remove_card(self, token: str) -> dict[str, Any]:
        return await self.cards.remove(token)

    async def create_receipt(
        self,
        order_id: str,
        amount: Decimal | int | str,
        order_type: str | None = None,
    ) -> dict[str, Any]:
        return await self.receipts.create(order_id, amount, order_type)

    async def pay_receipt(self, receipt_id: str, token: str) -> dict[str, Any]:
        return await self.receipts.pay(receipt_id, token)

    async def cancel_receipt(self, receipt_id: str) -> dict[str, Any]:
        return await self.receipts.cancel(receipt_id)

    async def create_initialization_link(
        self,
        amount: Decimal | int | str,
        order_id: str,
        return_url: str,
        order_type: str | None = None,
    ) -> str:
        return self.checkout_link(
            order_id=order_id,
            amount=amount,
            return_url=return_url,
            order_type=order_type,
        )

    async def close(self) -> None:
        """Close the session, unless the caller supplied one."""
        await self.transport.close()

    async def __aenter__(self) -> PaymeAPIClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
