from __future__ import annotations

import asyncio
import base64
import itertools
import logging
import os
from decimal import Decimal, InvalidOperation
from typing import Any

from aiohttp import ClientConnectionError, ClientSession, ClientTimeout
from dotenv import load_dotenv

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load environment variables from .env file
load_dotenv()


# Values under these keys are card credentials and must never reach a log file.
_SECRET_KEYS = frozenset({"token", "number", "expire"})


def _redact(value: Any) -> Any:
    """Copy a payload with card tokens and card data masked, for logging.

    A card token is a bearer credential: together with the cashbox key it can
    charge the card, so only enough of it to correlate requests is kept.
    """
    if isinstance(value, dict):
        return {
            k: (_mask(v) if k in _SECRET_KEYS and isinstance(v, str) else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _mask(secret: str) -> str:
    if len(secret) <= 8:
        return "***"
    return f"{secret[:8]}...({len(secret)} chars)"


def _normalize_card(number: str, expire: str) -> tuple[str, str]:
    """Accept the card as a human writes it and return what the API wants.

    Payme wants digits only, and an expiry as MMYY - "8600 0691 9540 6311" and
    "10/27" are what a card actually shows, and sending either verbatim comes
    back as -32602 Invalid Params.
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


def _to_tiyin(amount: Decimal | int | str) -> int:
    """Normalize an amount to a whole number of tiyin (1/100 so'm).

    Payme expects an integer amount, so fractional values are rejected instead
    of being silently truncated or sent as a float.
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


class PaymeAPIClient:
    TEST_URL = "https://checkout.test.paycom.uz/api"
    PRODUCTION_URL = "https://checkout.paycom.uz/api"
    INITIALIZATION_URL = "https://checkout.paycom.uz/"
    TEST_INITIALIZATION_URL = "https://checkout.test.paycom.uz"

    DEFAULT_TIMEOUT = 30  # seconds
    MAX_RETRIES = 10

    def __init__(
        self,
        session: ClientSession | None = None,
        *,
        token: str | None = None,
        secret_key: str | None = None,
        account_key: str | None = None,
        account_type_key: str | None = None,
        production: bool | None = None,
    ):
        """Create a client.

        Every setting falls back to its environment variable, read here rather
        than at import time, so ``os.environ`` / ``monkeypatch`` changes made
        after importing this module still take effect.
        """
        self.token = token if token is not None else os.getenv("PAYME_TOKEN")
        self.secret_key = (
            secret_key if secret_key is not None else os.getenv("PAYME_SECRET_KEY")
        )
        self.account_key = (
            account_key if account_key is not None else os.getenv("PAYME_ACCOUNT_KEY_1")
        )
        self.account_type_key = (
            account_type_key
            if account_type_key is not None
            else os.getenv("PAYME_ACCOUNT_KEY_2", "order_type")
        )
        self.production = (
            production
            if production is not None
            else os.getenv("PAYME_ENV", "false").lower() == "true"
        )

        missing = [
            name
            for name, value in (
                ("PAYME_TOKEN", self.token),
                ("PAYME_SECRET_KEY", self.secret_key),
                ("PAYME_ACCOUNT_KEY_1", self.account_key),
            )
            if not value
        ]
        if missing:
            logger.warning(
                "[Payme API] Missing configuration: %s. "
                "Requests will fail with an authorization error.",
                ", ".join(missing),
            )

        self.url = self.PRODUCTION_URL if self.production else self.TEST_URL
        self.link = (
            self.INITIALIZATION_URL if self.production else self.TEST_INITIALIZATION_URL
        )
        # Payme's JSON-RPC envelope carries a request id; every example in the
        # docs sends one and it comes back on the response.
        self._request_ids = itertools.count(1)
        # Only a session created here may be closed by close().
        self._owns_session = session is None
        self.session = session or ClientSession(
            timeout=ClientTimeout(total=self.DEFAULT_TIMEOUT)
        )

    @property
    def authorization(self) -> dict[str, str]:
        """Auth header for card methods."""
        return {"X-Auth": self.token}

    @property
    def auth_receipt(self) -> dict[str, str]:
        """Auth header for receipt methods."""
        return {"X-Auth": f"{self.token}:{self.secret_key}"}

    async def _request_with_retry(
        self,
        data: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        data = {"id": next(self._request_ids), **data}
        attempt = 0
        while attempt < self.MAX_RETRIES:
            try:
                async with self.session.post(
                    url=self.url, json=data, headers=headers
                ) as response:
                    try:
                        result = await response.json()
                    except Exception:
                        logger.exception("[Payme API] Error parsing JSON response")
                        raise
                    else:
                        if response.status != 200:
                            logger.error(
                                "Payme API non-200 response (%s): %s",
                                response.status,
                                result,
                            )
                        logger.info(
                            "[Payme API] %s Response: %s",
                            data["method"],
                            _redact(result),
                        )
                        return result
            except ClientConnectionError as err:
                attempt += 1
                logger.warning(
                    "[Payme API] Connection error attempt %s/%s: %s",
                    attempt,
                    self.MAX_RETRIES,
                    err,
                )
                if attempt >= self.MAX_RETRIES:
                    logger.exception(
                        "[Payme API] Max retries exceeded for %s", data["method"]
                    )
                    raise
                await asyncio.sleep(1)
            except Exception:
                logger.exception("[Payme API] Unexpected error on %s", data["method"])
                raise
        # MAX_RETRIES <= 0 is the only way out of the loop without a response.
        raise RuntimeError(
            f"[Payme API] No request attempted for {data['method']}: "
            f"MAX_RETRIES is {self.MAX_RETRIES}"
        )

    async def create_receipt(
        self, order_id: str, amount: Decimal, order_type: str | None = None
    ) -> dict[str, Any]:
        try:
            account = {self.account_key: order_id}
            # Payme rejects null account subfields, so only send it when set.
            if order_type is not None:
                account[self.account_type_key] = order_type
            data = {
                "method": "receipts.create",
                "params": {"amount": _to_tiyin(amount), "account": account},
            }
            return await self._request_with_retry(data, self.auth_receipt)
        except Exception:
            logger.exception("[Payme API] Error in create_receipt")
            raise

    async def pay_receipt(self, receipt_id: str, token: str) -> dict[str, Any]:
        try:
            data = {
                "method": "receipts.pay",
                "params": {"id": receipt_id, "token": token},
            }
            return await self._request_with_retry(data, self.auth_receipt)
        except Exception:
            logger.exception("[Payme API] Error in pay_receipt")
            raise

    async def create_initialization_link(
        self,
        amount: Decimal,
        order_id: str,
        return_url: str,
        order_type: str | None = None,
    ) -> str:
        try:
            params = (
                f"m={self.token};ac.{self.account_key}={order_id};"
                f"a={_to_tiyin(amount)};c={return_url}"
            )
            if order_type:
                params += f";ac.{self.account_type_key}={order_type}"
            encode_params = base64.b64encode(params.encode("utf-8")).decode("utf-8")
            link = f"{self.link}/{encode_params}"
            logger.info("[Payme API] Generated initialization link: %s", link)
        except Exception:
            logger.exception("[Payme API] Error in create_initialization_link")
            raise
        else:
            return link

    async def create_card(
        self, card_number: str, expire: str, save: bool = False
    ) -> dict[str, Any]:
        try:
            number, expire = _normalize_card(card_number, expire)
            data = {
                "method": "cards.create",
                "params": {
                    "card": {"number": number, "expire": expire},
                    "save": save,
                },
            }
            return await self._request_with_retry(data, self.authorization)
        except Exception:
            logger.exception("[Payme API] Error in create_card")
            raise

    async def get_card_verify_code(self, token: str) -> dict[str, Any]:
        try:
            result = await self._request_with_retry(
                {"method": "cards.get_verify_code", "params": {"token": token}},
                self.authorization,
            )
        except Exception:
            logger.exception("[Payme API] Error in get_card_verify_code")
            raise
        else:
            # Append token for consistency, without mutating the API response.
            return {**result, "token": token}

    async def check_card(self, token: str) -> dict[str, Any]:
        """Check that a card token is still usable."""
        try:
            data = {"method": "cards.check", "params": {"token": token}}
            return await self._request_with_retry(data, self.authorization)
        except Exception:
            logger.exception("[Payme API] Error in check_card")
            raise

    async def remove_card(self, token: str) -> dict[str, Any]:
        """Revoke a card token. The token stops working immediately."""
        try:
            data = {"method": "cards.remove", "params": {"token": token}}
            return await self._request_with_retry(data, self.authorization)
        except Exception:
            logger.exception("[Payme API] Error in remove_card")
            raise

    async def verify_card(self, code: str, token: str) -> dict[str, Any]:
        try:
            data = {
                "method": "cards.verify",
                "params": {"token": token, "code": str(code)},
            }
            return await self._request_with_retry(data, self.authorization)
        except Exception:
            logger.exception("[Payme API] Error in verify_card")
            raise

    async def cancel_receipt(self, receipt_id: str) -> dict[str, Any]:
        try:
            data = {
                "method": "receipts.cancel",
                "params": {"id": receipt_id},
            }
            return await self._request_with_retry(data, self.auth_receipt)
        except Exception:
            logger.exception("[Payme API] Error in cancel_receipt")
            raise

    async def close(self):
        """Close the aiohttp session, but only if this client created it.

        A session passed into __init__ belongs to the caller and is left open.
        """
        try:
            if self._owns_session and self.session and not self.session.closed:
                await self.session.close()
        except Exception:
            logger.exception("[Payme API] Error in close")
            raise
