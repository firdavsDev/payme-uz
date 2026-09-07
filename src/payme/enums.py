from __future__ import annotations

from enum import Enum

# Descriptions are keyed by the numeric code rather than by member, because several
# Payme codes carry more than one meaning and the API gives no way to tell them
# apart. Those descriptions list every meaning the code can have.
ERROR_DESCRIPTIONS: dict[int, str] = {
    200: "Success",
    # General JSON-RPC errors
    -32300: "Transport error",
    -32700: "Parse error",
    -32600: "Invalid request",
    -32400: "System error",
    -32601: "Method not found",
    -32602: "Invalid params",
    -32504: "Access denied",
    # Cards module errors
    -31301: "SMS notification not connected, card expired, or card blocked",
    -31300: "Invalid card number, or financial operations forbidden for corporate cards",
    -31302: "Unable to get card balance, try later",
    -31303: "Insufficient funds on card",
    -31002: "Processing center unavailable",
    -31400: "Card not found",
    -31151: "Card already attached",
    # Card verification errors (otp)
    -31200: "Verification code invalid",
    -31201: "Verification code expired",
    -31101: "Verification code lifetime expired, card deleted or blocked, or card not serviced",
    -31102: "Number of attempts exceeded, request a new code",
    -31103: "Incorrect verification code",
    # Receipt errors
    -31008: "Receipt not found",
    -31800: "Receipt cannot be canceled automatically, or receipt status changed - check and try later",
    -31602: "Receipt not found or already paid",
    -31001: "No access to this receipt, or invalid amount",
    -31601: "Merchant in maintenance, or merchant not found",
    -31700: "Receipt is blacklisted, or too many payment attempts on this account",
    -31613: "Currency not allowed for provider",
    -31623: "Service provider error",
    # Transaction errors
    -31007: "Transaction not permitted",
    -31050: "Order not found",
    -31051: "Insufficient funds",
    # Other card errors
    -31100: "Processing center error",
    -31630: "Invalid expiration date, PIN code attempts exceeded (card blocked), or corporate card payments forbidden",
    -31900: "Card type not supported",
    -31901: "Transaction type not supported",
    # OTP module errors
    -31110: "Error sending SMS, try again",
    # Fallback
    -1: "Unknown error",
}


class PaymeErrorCode(Enum):
    """Payme JSON-RPC error codes.

    Payme reuses a single numeric code for several distinct failures, so some
    names below are Enum aliases of an earlier member rather than members of
    their own: ``PaymeErrorCode.CARD_EXPIRED is PaymeErrorCode.SMS_NOT_CONNECTED``
    is ``True``. Aliases are marked in the comments. Never branch on an alias
    name expecting it to be distinguishable - ``get_error_enum`` can only ever
    return the canonical member for a given code, and ``description`` reports
    every meaning that code can carry.
    """

    # Common success
    SUCCESS = 200

    # General JSON-RPC errors
    TRANSPORT_ERROR = -32300
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    SYSTEM_ERROR = -32400
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    ACCESS_DENIED = -32504

    # Cards module errors
    SMS_NOT_CONNECTED = -31301
    # alias of SMS_NOT_CONNECTED
    CARD_EXPIRED = -31301  # noqa: PIE796
    # alias of SMS_NOT_CONNECTED
    CARD_BLOCKED = -31301  # noqa: PIE796
    FINANCIAL_OPERATIONS_FOR_CORP_CARDS_FORBIDDEN = -31300
    BALANCE_UNAVAILABLE_TRY_LATER = -31302
    INSUFFICIENT_FUNDS_ON_CARD = -31303
    PROCESSING_CENTER_UNAVAILABLE = -31002
    # alias of FINANCIAL_OPERATIONS_FOR_CORP_CARDS_FORBIDDEN
    INVALID_CARD_NUMBER = -31300  # noqa: PIE796
    CARD_NOT_FOUND = -31400
    CARD_ALREADY_ATTACHED = -31151

    # Card verification errors (otp)
    VERIFY_CODE_INVALID = -31200
    VERIFY_CODE_EXPIRED = -31201
    VERIFY_CODE_EXPIRED_ALT = -31101
    VERIFY_CODE_ATTEMPTS_EXCEEDED = -31102
    VERIFY_CODE_INCORRECT = -31103

    # Receipt errors
    RECEIPT_NOT_FOUND = -31008
    RECEIPT_CANNOT_CANCEL_AUTOMATICALLY = -31800
    # alias of RECEIPT_CANNOT_CANCEL_AUTOMATICALLY
    RECEIPT_STATUS_CHANGED = -31800  # noqa: PIE796
    RECEIPT_ALREADY_PAID_OR_NOT_FOUND = -31602
    RECEIPT_ACCESS_DENIED = -31001
    RECEIPT_MERCHANT_MAINTENANCE = -31601
    RECEIPT_BLACKLISTED = -31700
    # alias of RECEIPT_BLACKLISTED
    RECEIPT_TOO_MANY_ATTEMPTS = -31700  # noqa: PIE796
    RECEIPT_CURRENCY_NOT_ALLOWED = -31613
    RECEIPT_SERVICE_PROVIDER_ERROR = -31623
    # alias of VERIFY_CODE_EXPIRED_ALT
    RECEIPT_CARD_NOT_SERVICED = -31101  # noqa: PIE796

    # Transaction errors
    TRANSACTION_NOT_PERMITTED = -31007
    ORDER_NOT_FOUND = -31050
    # alias of RECEIPT_ACCESS_DENIED
    INVALID_AMOUNT = -31001  # noqa: PIE796
    INSUFFICIENT_FUNDS = -31051
    # alias of RECEIPT_MERCHANT_MAINTENANCE
    MERCHANT_NOT_FOUND = -31601  # noqa: PIE796

    # Other card errors
    # alias of VERIFY_CODE_EXPIRED_ALT
    CARD_DELETED_OR_BLOCKED = -31101  # noqa: PIE796
    PROCESSING_CENTER_ERROR = -31100
    INVALID_EXPIRATION_DATE = -31630
    CARD_NOT_SUPPORTED = -31900
    # alias of INVALID_EXPIRATION_DATE
    CARD_PIN_ATTEMPTS_EXCEEDED = -31630  # noqa: PIE796
    # alias of INVALID_EXPIRATION_DATE
    CORPORATE_CARD_PAYMENT_FORBIDDEN = -31630  # noqa: PIE796
    TRANSACTION_TYPE_NOT_SUPPORTED = -31901

    # OTP module errors
    OTP_SEND_ERROR = -31110

    # Fallback
    UNKNOWN_ERROR = -1

    def description(self) -> str:
        """Return human-readable description of the error code."""
        return ERROR_DESCRIPTIONS.get(self.value, "Unknown error")

    @classmethod
    def get_error_enum(cls, error_code: int) -> PaymeErrorCode | None:
        try:
            return cls(error_code)
        except ValueError:
            return None
