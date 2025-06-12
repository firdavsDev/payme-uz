from enum import Enum

from enum import Enum


class PaymeErrorCode(Enum):
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
    CARD_EXPIRED = -31301
    CARD_BLOCKED = -31301
    FINANCIAL_OPERATIONS_FOR_CORP_CARDS_FORBIDDEN = -31300
    BALANCE_UNAVAILABLE_TRY_LATER = -31302
    INSUFFICIENT_FUNDS_ON_CARD = -31303
    PROCESSING_CENTER_UNAVAILABLE = -31002
    INVALID_CARD_NUMBER = -31300
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
    RECEIPT_STATUS_CHANGED = -31800
    RECEIPT_ALREADY_PAID_OR_NOT_FOUND = -31602
    RECEIPT_ACCESS_DENIED = -31001
    RECEIPT_MERCHANT_MAINTENANCE = -31601
    RECEIPT_BLACKLISTED = -31700
    RECEIPT_TOO_MANY_ATTEMPTS = -31700
    RECEIPT_CURRENCY_NOT_ALLOWED = -31613
    RECEIPT_SERVICE_PROVIDER_ERROR = -31623
    RECEIPT_CARD_NOT_SERVICED = -31101

    # Transaction errors
    TRANSACTION_NOT_PERMITTED = -31007
    ORDER_NOT_FOUND = -31050
    INVALID_AMOUNT = -31001
    INSUFFICIENT_FUNDS = -31051
    MERCHANT_NOT_FOUND = -31601

    # Other card errors
    CARD_DELETED_OR_BLOCKED = -31101
    PROCESSING_CENTER_ERROR = -31100
    INVALID_EXPIRATION_DATE = -31630
    CARD_NOT_SUPPORTED = -31900
    CARD_PIN_ATTEMPTS_EXCEEDED = -31630
    CORPORATE_CARD_PAYMENT_FORBIDDEN = -31630
    TRANSACTION_TYPE_NOT_SUPPORTED = -31901

    # OTP module errors
    OTP_SEND_ERROR = -31110

    # Fallback
    UNKNOWN_ERROR = -1

    def description(self) -> str:
        """Return human-readable description of the error code."""
        descriptions = {
            self.SUCCESS: "Success",
            self.TRANSPORT_ERROR: "Transport error",
            self.PARSE_ERROR: "Parse error",
            self.INVALID_REQUEST: "Invalid request",
            self.INVALID_RESPONSE: "Invalid response",
            self.SYSTEM_ERROR: "System error",
            self.METHOD_NOT_FOUND: "Method not found",
            self.INVALID_PARAMS: "Invalid params",
            self.ACCESS_DENIED: "Access denied",
            self.SMS_NOT_CONNECTED: "SMS notification not connected",
            self.CARD_EXPIRED: "Card expired",
            self.CARD_BLOCKED: "Card blocked",
            self.FINANCIAL_OPERATIONS_FOR_CORP_CARDS_FORBIDDEN: "Financial operations for corporate cards forbidden",
            self.BALANCE_UNAVAILABLE_TRY_LATER: "Unable to get card balance, try later",
            self.INSUFFICIENT_FUNDS_ON_CARD: "Insufficient funds on card",
            self.PROCESSING_CENTER_UNAVAILABLE: "Processing center unavailable",
            self.INVALID_CARD_NUMBER: "Invalid card number",
            self.CARD_NOT_FOUND: "Card not found",
            self.CARD_ALREADY_ATTACHED: "Card already attached",
            self.VERIFY_CODE_INVALID: "Verification code invalid",
            self.VERIFY_CODE_EXPIRED: "Verification code expired",
            self.VERIFY_CODE_EXPIRED_ALT: "Verification code lifetime expired, request a new code",
            self.VERIFY_CODE_ATTEMPTS_EXCEEDED: "Number of attempts exceeded, request a new code",
            self.VERIFY_CODE_INCORRECT: "Incorrect verification code",
            self.RECEIPT_NOT_FOUND: "Receipt not found",
            self.RECEIPT_CANNOT_CANCEL_AUTOMATICALLY: "Receipt cannot be canceled automatically",
            self.RECEIPT_STATUS_CHANGED: "Receipt status changed, check and try later",
            self.RECEIPT_ALREADY_PAID_OR_NOT_FOUND: "Receipt not found or already paid",
            self.RECEIPT_ACCESS_DENIED: "No access to this receipt",
            self.RECEIPT_MERCHANT_MAINTENANCE: "Merchant in maintenance",
            self.RECEIPT_BLACKLISTED: "Receipt is blacklisted",
            self.RECEIPT_TOO_MANY_ATTEMPTS: "Too many payment attempts on this account",
            self.RECEIPT_CURRENCY_NOT_ALLOWED: "Currency not allowed for provider",
            self.RECEIPT_SERVICE_PROVIDER_ERROR: "Service provider error",
            self.RECEIPT_CARD_NOT_SERVICED: "Card not serviced",
            self.TRANSACTION_NOT_PERMITTED: "Transaction not permitted",
            self.ORDER_NOT_FOUND: "Order not found",
            self.INVALID_AMOUNT: "Invalid amount",
            self.INSUFFICIENT_FUNDS: "Insufficient funds",
            self.MERCHANT_NOT_FOUND: "Merchant not found",
            self.CARD_DELETED_OR_BLOCKED: "Card deleted or blocked",
            self.PROCESSING_CENTER_ERROR: "Processing center error",
            self.INVALID_EXPIRATION_DATE: "Invalid expiration date",
            self.CARD_NOT_SUPPORTED: "Card type not supported",
            self.CARD_PIN_ATTEMPTS_EXCEEDED: "PIN code attempts exceeded, card blocked",
            self.CORPORATE_CARD_PAYMENT_FORBIDDEN: "Corporate card payments forbidden",
            self.TRANSACTION_TYPE_NOT_SUPPORTED: "Transaction type not supported",
            self.OTP_SEND_ERROR: "Error sending SMS, try again",
            self.UNKNOWN_ERROR: "Unknown error",
        }
        return descriptions.get(self, "Unknown error")

    @classmethod
    def get_error_enum(cls, error_code: int) -> "PaymeErrorCode | None":
        try:
            return cls(error_code)
        except ValueError:
            return None
