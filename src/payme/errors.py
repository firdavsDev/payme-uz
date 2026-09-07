"""Exceptions raised by the client.

Every failure surfaces as a subclass of :class:`PaymeError`, so a caller can
catch one type and still branch on specifics when it wants to::

    try:
        receipt = await client.receipts.create(order_id="42", amount=100_000)
    except MerchantEndpointError as e:
        # Payme reached your Merchant API endpoint and it refused.
        log.error("our endpoint said: %s", e.endpoint_error)
    except PaymeAPIError as e:
        log.error("payme said %s: %s", e.code, e)
"""

from __future__ import annotations

from typing import Any

from .enums import PaymeErrorCode


class PaymeError(Exception):
    """Base class for everything this package raises."""


class PaymeConfigError(PaymeError):
    """Configuration is missing or unusable before any request is made."""


class PaymeTransportError(PaymeError):
    """The request never produced a usable response.

    Raised when the connection fails and the retry policy is exhausted, or when
    the body is not JSON. The originating exception is kept as ``__cause__``.
    """

    def __init__(self, message: str, *, method: str | None = None) -> None:
        super().__init__(message)
        self.method = method


class PaymeAPIError(PaymeError):
    """Payme answered with a JSON-RPC error object."""

    def __init__(
        self,
        code: int,
        message: str,
        data: Any = None,
        *,
        method: str | None = None,
    ) -> None:
        super().__init__(message or f"Payme error {code}")
        self.code = code
        self.message = message
        self.data = data
        self.method = method

    @property
    def error_code(self) -> PaymeErrorCode | None:
        """The matching enum member, or ``None`` for a code Payme added later."""
        return PaymeErrorCode.get_error_enum(self.code)

    @property
    def description(self) -> str:
        """Every meaning the code can carry, from the documented list."""
        enum = self.error_code
        return enum.description() if enum else "Unknown error"

    def __str__(self) -> str:
        return f"[{self.code}] {self.message or self.description}"


class ProtocolError(PaymeAPIError):
    """Malformed request, unknown method, or a transport-level JSON-RPC fault."""


class AccessDeniedError(PaymeAPIError):
    """-32504. The cashbox id or key is not accepted on this host."""


class CardError(PaymeAPIError):
    """The card itself was rejected: blocked, expired, unknown, unsupported."""


class VerificationError(PaymeAPIError):
    """The SMS verification code was wrong, expired, or tried too often."""


class ReceiptError(PaymeAPIError):
    """The receipt could not be created, paid, or cancelled."""


class AccountFieldError(PaymeAPIError):
    """An ``account`` subfield is missing or unacceptable.

    ``field`` names the subfield Payme complained about.
    """

    @property
    def field(self) -> str | None:
        return self.data if isinstance(self.data, str) else None


class MerchantEndpointError(ReceiptError):
    """-31623. Your own Merchant API endpoint returned an error to Payme.

    ``endpoint_error`` is that server's reply verbatim; the outer message only
    says the provider service is misbehaving, which is rarely enough to debug.
    """

    @property
    def endpoint_error(self) -> Any:
        return self.data


# Codes Payme documents, grouped by what a caller would do about them.
_PROTOCOL_CODES = frozenset({-32300, -32700, -32600, -32400, -32601, -32602})
_VERIFICATION_CODES = frozenset({-31200, -31201, -31101, -31102, -31103})
_CARD_CODES = frozenset(
    {
        -31300,
        -31301,
        -31302,
        -31303,
        -31400,
        -31151,
        -31002,
        -31100,
        -31630,
        -31900,
        -31901,
    }
)
# -31050 and -31051 look like receipt failures but fall inside the
# account-field range, which exception_for checks first; listing them
# here too would be dead code.
_RECEIPT_CODES = frozenset(
    {
        -31008,
        -31800,
        -31602,
        -31001,
        -31601,
        -31700,
        -31613,
        -31007,
        -31110,
    }
)


def exception_for(code: int) -> type[PaymeAPIError]:
    """Pick the most specific exception class for a Payme error code."""
    if code == -31623:
        return MerchantEndpointError
    if code == -32504:
        return AccessDeniedError
    if code == -31610 or -31099 <= code <= -31050:
        return AccountFieldError
    if code in _PROTOCOL_CODES:
        return ProtocolError
    if code in _VERIFICATION_CODES:
        return VerificationError
    if code in _CARD_CODES:
        return CardError
    if code in _RECEIPT_CODES:
        return ReceiptError
    return PaymeAPIError


def from_error_object(
    error: dict[str, Any], *, method: str | None = None
) -> PaymeAPIError:
    """Build the exception for a JSON-RPC ``error`` object."""
    code = error.get("code", 0)
    message = error.get("message") or ""
    if isinstance(message, dict):  # Payme sometimes localizes: {"ru": ..., "en": ...}
        message = (
            message.get("en") or message.get("ru") or next(iter(message.values()), "")
        )
    return exception_for(code)(code, message, error.get("data"), method=method)
