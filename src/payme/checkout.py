"""Checkout links - the one part of the flow that needs no HTTP call."""

from __future__ import annotations

import base64
from decimal import Decimal

from .config import PaymeConfig
from .validation import to_tiyin


def build_checkout_link(
    config: PaymeConfig,
    *,
    order_id: str,
    amount: Decimal | int | str,
    return_url: str,
    order_type: str | None = None,
) -> str:
    """Build the hosted-checkout URL the customer opens.

    The parameters are base64 of a ``m=...;ac.<key>=...;a=...;c=...`` string;
    ``a`` is in tiyin, like every other amount.
    """
    config.require("token", "account_key")
    params = (
        f"m={config.token};ac.{config.account_key}={order_id};"
        f"a={to_tiyin(amount)};c={return_url}"
    )
    if order_type:
        params += f";ac.{config.account_type_key}={order_type}"
    encoded = base64.b64encode(params.encode("utf-8")).decode("utf-8")
    return f"{config.checkout_url}/{encoded}"
