from payme.testing import SMS_VERIFY_CODE, TEST_CARD_EXPIRE, TEST_CARDS


def test_card_numbers_are_well_formed_and_unique():
    numbers = [card.number for card in TEST_CARDS]
    assert len(numbers) == len(set(numbers))
    for number in numbers:
        assert number.isdigit()
        assert len(number) == 16


def test_every_card_documents_a_behavior_and_shares_the_expiry():
    for card in TEST_CARDS:
        assert card.behavior
        assert card.expire == TEST_CARD_EXPIRE == "0399"


def test_sms_code():
    assert SMS_VERIFY_CODE == "666666"
