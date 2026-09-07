from decimal import Decimal

import pytest

from payme.validation import normalize_card, to_tiyin


@pytest.mark.parametrize("amount", [Decimal(100000), 100000, "100000"])
def test_whole_amounts_pass_through(amount):
    assert to_tiyin(amount) == 100000


def test_fractional_amount_is_rejected_not_truncated():
    with pytest.raises(ValueError, match="whole number of tiyin"):
        to_tiyin(Decimal("100.5"))


def test_nonsense_amount():
    with pytest.raises(ValueError, match="Invalid amount"):
        to_tiyin("abc")


@pytest.mark.parametrize(
    ("number", "expire"),
    [
        ("8600 0691 9540 6311", "10/27"),
        ("8600069195406311", "1027"),
        ("8600 0691 9540 6311", "1027"),
    ],
)
def test_card_input_is_normalized(number, expire):
    assert normalize_card(number, expire) == ("8600069195406311", "1027")


@pytest.mark.parametrize(
    ("number", "expire", "message"),
    [
        ("8600069195406311", "99/27", "month must be 01-12"),
        ("8600069195406311", "1/27", "MMYY or MM/YY"),
        ("8600-0691-9540-6311", "1027", "12-19 digits"),
        ("860006919", "1027", "12-19 digits"),
    ],
)
def test_bad_card_input_names_the_field(number, expire, message):
    with pytest.raises(ValueError, match=message):
        normalize_card(number, expire)
