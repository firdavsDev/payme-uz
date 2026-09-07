"""Input normalization, so a bad value fails here instead of as -32602."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def to_tiyin(amount: Decimal | int | str) -> int:
    """Normalize an amount to a whole number of tiyin (1/100 so'm).

    Payme expects an integer, so a fractional value is rejected rather than
    silently truncated or sent as a float.
    """
    try:
        value = Decimal(amount)
    except (InvalidOperation, TypeError, ValueError) as e:
        raise ValueError(f"Invalid amount: {amount!r}") from e
    if value != value.to_integral_value():
        raise ValueError(
            f"Amount must be a whole number of tiyin (1/100 so'm), got {amount!r}"
        )
    return int(value)


def normalize_card(number: str, expire: str) -> tuple[str, str]:
    """Accept a card as a human writes it and return what the API wants.

    Payme wants digits only and an expiry as MMYY, so "8600 0691 9540 6311"
    and "10/27" - what the card itself shows - are normalized here instead of
    coming back as -32602 Invalid Params with no field name.
    """
    digits = "".join(number.split())
    expire_digits = expire.replace("/", "").replace(" ", "")
    if not digits.isdigit() or not 12 <= len(digits) <= 19:
        raise ValueError(f"Card number must be 12-19 digits, got {number!r}")
    if not expire_digits.isdigit() or len(expire_digits) != 4:
        raise ValueError(f"Card expiry must be MMYY or MM/YY, got {expire!r}")
    if not 1 <= int(expire_digits[:2]) <= 12:
        raise ValueError(f"Card expiry month must be 01-12, got {expire!r}")
    return digits, expire_digits
