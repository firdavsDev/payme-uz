from enum import Enum


class PaymeErrorCode(Enum):
    SUCCESS = 200
    INVALID_AMOUNT = -31001
    ORDER_NOT_FOUND = -31050
    TRANSACTION_NOT_PERMITTED = -31007
    CARD_NOT_FOUND = -31100
    CARD_ALREADY_ATTACHED = -31151
    VERIFY_CODE_INVALID = -31200
    VERIFY_CODE_EXPIRED = -31201
    RECEIPT_NOT_FOUND = -31008
    INSUFFICIENT_FUNDS = -31051

    @classmethod
    def get_error_enum(cls, error_code: int) -> "PaymeErrorCode | None":
        try:
            return cls(error_code)
        except ValueError:
            return None
