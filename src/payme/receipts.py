"""Receipt methods of the Subscribe API.

These authenticate with ``id:key``. None of them is retried: a replayed
``receipts.pay`` can charge a card twice, and a replayed ``receipts.create``
leaves duplicate receipts against one order.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .config import PaymeConfig
from .transport import JsonRpcTransport
from .validation import to_tiyin


class ReceiptsAPI:
    """``receipts.*`` methods, reachable as ``client.receipts``."""

    def __init__(self, transport: JsonRpcTransport, config: PaymeConfig) -> None:
        self._transport = transport
        self._config = config

    async def create(
        self,
        order_id: str,
        amount: Decimal | int | str,
        order_type: str | None = None,
    ) -> dict[str, Any]:
        """Create a receipt for an order. ``amount`` is in tiyin (1/100 so'm)."""
        self._config.require("account_key")
        account = {self._config.account_key: order_id}
        # Payme rejects a null account subfield, so only send it when set.
        if order_type is not None:
            account[self._config.account_type_key] = order_type
        return await self._transport.call(
            "receipts.create",
            {"amount": to_tiyin(amount), "account": account},
            self._config.receipt_auth,
        )

    async def pay(self, receipt_id: str, token: str) -> dict[str, Any]:
        """Charge a verified card token for a receipt."""
        return await self._transport.call(
            "receipts.pay",
            {"id": receipt_id, "token": token},
            self._config.receipt_auth,
        )

    async def cancel(self, receipt_id: str) -> dict[str, Any]:
        """Cancel a receipt."""
        return await self._transport.call(
            "receipts.cancel", {"id": receipt_id}, self._config.receipt_auth
        )
