from decimal import Decimal
from typing import Optional

from payme.client import PaymeAPIClient


class PaymeService:
    def __init__(self, client: Optional[PaymeAPIClient] = None):
        self.client = client or PaymeAPIClient()

    async def create_and_pay_transaction(
        self,
        token: str,
        order_id: str,
        amount: Decimal,
        order_type: Optional[str] = None,
    ) -> dict:
        receipt_response = await self.client.create_receipt(
            order_id, amount, order_type
        )

        # Check for error
        if "error" in receipt_response:
            return receipt_response

        receipt_id = receipt_response["result"]["receipt"]["_id"]
        pay_response = await self.client.pay_receipt(receipt_id, token)
        return pay_response

    async def create_payment_link(
        self,
        amount: Decimal,
        order_id: str,
        return_url: str,
        order_type: Optional[str] = None,
    ) -> str:
        return await self.client.create_initialization_link(
            amount, order_id, return_url, order_type
        )

    async def close(self):
        await self.client.close()
