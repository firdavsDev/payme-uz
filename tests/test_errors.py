from payme.enums import PaymeErrorCode
from payme.errors import (
    AccessDeniedError,
    AccountFieldError,
    CardError,
    MerchantEndpointError,
    PaymeAPIError,
    ProtocolError,
    ReceiptError,
    VerificationError,
    exception_for,
    from_error_object,
)


def test_codes_map_to_the_class_a_caller_would_catch():
    assert exception_for(-32504) is AccessDeniedError
    assert exception_for(-32602) is ProtocolError
    assert exception_for(-31301) is CardError
    assert exception_for(-31103) is VerificationError
    assert exception_for(-31008) is ReceiptError
    assert exception_for(-31610) is AccountFieldError
    assert exception_for(-31055) is AccountFieldError  # -31050..-31099 range
    assert exception_for(-31623) is MerchantEndpointError
    assert exception_for(-99999) is PaymeAPIError  # a code Payme adds later


def test_error_object_becomes_a_typed_exception():
    error = from_error_object(
        {"code": -31400, "message": "Карта не найдена.", "data": "deleted"},
        method="cards.check",
    )
    assert isinstance(error, CardError)
    assert error.code == -31400
    assert error.data == "deleted"
    assert error.method == "cards.check"
    assert error.error_code is PaymeErrorCode.CARD_NOT_FOUND
    assert "Card not found" in error.description


def test_localized_messages_are_flattened():
    error = from_error_object(
        {"code": -32504, "message": {"ru": "Нет", "en": "Denied"}}
    )
    assert str(error) == "[-32504] Denied"


def test_merchant_endpoint_error_exposes_the_nested_reply():
    error = from_error_object(
        {
            "code": -31623,
            "message": "Сервис поставщика услуг работает некорректно",
            "data": {"code": -32504, "message": {"en": "Insufficient privileges."}},
        }
    )
    assert isinstance(error, MerchantEndpointError)
    # The useful half is nested: the outer message never says what went wrong.
    assert error.endpoint_error["code"] == -32504


def test_account_field_error_names_the_field():
    error = from_error_object({"code": -31610, "message": "", "data": "order_id"})
    assert isinstance(error, AccountFieldError)
    assert error.field == "order_id"


def test_unknown_code_still_has_a_readable_string():
    error = from_error_object({"code": -12345, "message": ""})
    assert error.error_code is None
    assert str(error) == "[-12345] Unknown error"


def test_account_field_range_wins_over_receipt_codes():
    # -31050 (order not found) and -31051 sit inside -31050..-31099, which Payme
    # documents as "the account subfield in `data` was wrong".
    assert exception_for(-31050) is AccountFieldError
    assert exception_for(-31051) is AccountFieldError
    assert exception_for(-31008) is ReceiptError
