import asyncio
import base64
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from aiohttp import ClientSession, ClientConnectionError, ClientTimeout
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Configurations
PAYME_ENV = os.getenv("PAYME_ENV", "false").lower() == "true"
TOKEN = os.getenv("PAYME_TOKEN")
AUTHORIZATION = {"X-Auth": TOKEN}
SECRET_KEY = os.getenv("PAYME_SECRET_KEY")
KEY_1 = os.getenv("PAYME_ACCOUNT_KEY_1")
KEY_2 = os.getenv("PAYME_ACCOUNT_KEY_2", "order_type")
AUTH_RECEIPT = {"X-Auth": f"{TOKEN}:{SECRET_KEY}"}


class PaymeAPIClient:
    TEST_URL = "https://checkout.test.payme.uz/api"
    PRODUCTION_URL = "https://checkout.paycom.uz/api"
    INITIALIZATION_URL = "https://checkout.paycom.uz/"
    TEST_INITIALIZATION_URL = "https://checkout.test.payme.uz"

    DEFAULT_TIMEOUT = 10  # seconds
    MAX_RETRIES = 10

    def __init__(self, session: Optional[ClientSession] = None):
        self.url = self.PRODUCTION_URL if PAYME_ENV else self.TEST_URL
        self.link = (
            self.INITIALIZATION_URL if PAYME_ENV else self.TEST_INITIALIZATION_URL
        )
        self.session = session or ClientSession(
            timeout=ClientTimeout(total=self.DEFAULT_TIMEOUT)
        )

    async def _request_with_retry(
        self,
        data: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        attempt = 0
        while attempt < self.MAX_RETRIES:
            try:
                async with self.session.post(
                    url=self.url, json=data, headers=headers
                ) as response:
                    result = await response.json()

                    if response.status != 200:
                        logger.warning(
                            f"Payme API non-200 response ({response.status}): {result}"
                        )

                    logger.info(f"[Payme API] {data['method']} Response: {result}")
                    return result
            except ClientConnectionError as err:
                attempt += 1
                logger.warning(
                    f"[Payme API] Connection error attempt {attempt}/{self.MAX_RETRIES}: {err}"
                )
                if attempt >= self.MAX_RETRIES:
                    logger.error(
                        f"[Payme API] Max retries exceeded for {data['method']}"
                    )
                    raise err
                await asyncio.sleep(1)
            except Exception as e:
                logger.exception(
                    f"[Payme API] Unexpected error on {data['method']}: {e}"
                )
                raise e

    async def create_receipt(
        self, order_id: str, amount: Decimal, order_type: Optional[str] = None
    ) -> Dict[str, Any]:
        data = {
            "method": "receipts.create",
            "params": {
                "amount": float(amount),
                "account": {KEY_1: order_id, KEY_2: order_type},
            },
        }
        return await self._request_with_retry(data, AUTH_RECEIPT)

    async def pay_receipt(self, receipt_id: str, token: str) -> Dict[str, Any]:
        data = {
            "method": "receipts.pay",
            "params": {"id": receipt_id, "token": token},
        }
        return await self._request_with_retry(data, AUTH_RECEIPT)

    async def create_initialization_link(
        self,
        amount: Decimal,
        order_id: str,
        return_url: str,
        order_type: Optional[str] = None,
    ) -> str:
        params = f"m={TOKEN};ac.{KEY_1}={order_id};a={amount};c={return_url}"
        if order_type:
            params += f";ac.{KEY_2}={order_type}"
        encode_params = base64.b64encode(params.encode("utf-8")).decode("utf-8")
        link = f"{self.link}/{encode_params}"
        logger.info(f"[Payme API] Generated initialization link: {link}")
        return link

    async def create_card(
        self, card_number: str, expire: str, save: bool = False
    ) -> Dict[str, Any]:
        data = {
            "method": "cards.create",
            "params": {"card": {"number": card_number, "expire": expire}, "save": save},
        }
        return await self._request_with_retry(data, AUTHORIZATION)

    async def get_card_verify_code(self, token: str) -> Dict[str, Any]:
        data = {
            "method": "cards.get_verify_code",
            "params": {"token": token},
        }
        result = await self._request_with_retry(data, AUTHORIZATION)
        result.update(token=token)  # Append token for consistency
        return result

    async def verify_card(self, code: str, token: str) -> Dict[str, Any]:
        data = {
            "method": "cards.verify",
            "params": {"token": token, "code": str(code)},
        }
        return await self._request_with_retry(data, AUTHORIZATION)

    async def cancel_receipt(self, receipt_id: str) -> Dict[str, Any]:
        data = {
            "method": "receipts.cancel",
            "params": {"id": receipt_id},
        }
        return await self._request_with_retry(data, AUTH_RECEIPT)

    async def close(self):
        """Gracefully close aiohttp session if it was created inside the class."""
        if self.session and not self.session.closed:
            await self.session.close()
