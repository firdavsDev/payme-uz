from payme.enums import ERROR_DESCRIPTIONS, PaymeErrorCode


def test_description_works_for_every_member():
    for member in PaymeErrorCode:
        description = member.description()
        assert description
        if member is not PaymeErrorCode.UNKNOWN_ERROR:
            assert description != "Unknown error"


def test_every_member_has_a_description_entry():
    assert {m.value for m in PaymeErrorCode} == set(ERROR_DESCRIPTIONS)


def test_unmapped_code_falls_back():
    assert PaymeErrorCode.get_error_enum(-99999) is None


def test_aliases_resolve_to_canonical_member():
    # Payme reuses -31301; the aliases must stay aliases, not separate members.
    assert PaymeErrorCode.CARD_EXPIRED is PaymeErrorCode.SMS_NOT_CONNECTED
    assert PaymeErrorCode.get_error_enum(-31301) is PaymeErrorCode.SMS_NOT_CONNECTED
    description = PaymeErrorCode.get_error_enum(-31301).description()
    assert "card expired" in description and "card blocked" in description
