"""Sandbox constants published in the Payme Business documentation.

Test cards only work against the test host (``PAYME_ENV`` unset or "false",
i.e. ``https://checkout.test.paycom.uz/api``) with a cashbox registered in the
test cabinet at https://merchant.test.paycom.uz - a production merchant id is
rejected there with ``-32504`` / ``invalid_id``.
"""

from __future__ import annotations

from dataclasses import dataclass

# The verification code cards.get_verify_code "sends" for every test card.
SMS_VERIFY_CODE = "666666"

# Every test card carries the same expiry, in the MMYY format the API wants.
TEST_CARD_EXPIRE = "0399"


@dataclass(frozen=True)
class TestCard:
    """A sandbox card and the behaviour it simulates."""

    number: str
    behavior: str
    expire: str = TEST_CARD_EXPIRE


# Cards that complete the flow normally.
CARD_OK = "8600495473316478"
CARD_OK_ALT = "8600069195406311"

# Cards that fail in a specific, documented way.
CARD_SMS_NOT_CONNECTED = "8600060921090842"
CARD_EXPIRED = "3333336415804657"
CARD_BLOCKED = "4444445987459073"
CARD_SYSTEM_ERROR = "8600143417770323"
CARD_SLOW_THEN_ERROR = "8600134301849596"

TEST_CARDS: tuple[TestCard, ...] = (
    TestCard(CARD_OK, "Succeeds"),
    TestCard(CARD_OK_ALT, "Succeeds"),
    TestCard(CARD_SMS_NOT_CONNECTED, "SMS notification is not connected"),
    TestCard(CARD_EXPIRED, "Card expired"),
    TestCard(CARD_BLOCKED, "Card blocked"),
    TestCard(CARD_SYSTEM_ERROR, "Unknown system error"),
    TestCard(CARD_SLOW_THEN_ERROR, "Delays ~10 seconds, then fails"),
)
