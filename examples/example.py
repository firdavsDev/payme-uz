import asyncio
import logging
from decimal import Decimal

from payme.client import PaymeAPIClient
from payme.enums import PaymeErrorCode
from payme.log import setup_logger
from payme.testing import CARD_OK_ALT, SMS_VERIFY_CODE, TEST_CARD_EXPIRE

# Initialize logger
logger = setup_logger("payme_example", level=logging.INFO)

# Example params (replace these with real values for your test)
# Sandbox card: only works against checkout.test.paycom.uz with a cashbox from
# the test cabinet at https://merchant.test.paycom.uz
CARD_NUMBER = CARD_OK_ALT
CARD_EXPIRE = TEST_CARD_EXPIRE  # MMYY
COURSE_PRICE = 1000  # so'm
RETURN_URL = "https://yourapp.com/return"

USER_ID = 12345  # Example user ID


async def main():
    payme_client = PaymeAPIClient()
    try:
        logger.info("=== Payme Example ===")

        # Step 1️⃣ Create card
        logger.info("1️⃣ Creating card...")
        response = await payme_client.create_card(CARD_NUMBER, CARD_EXPIRE, save=False)
        print(
            "Response after creating card:", response
        )  # Print the response for debugging

        # Check for errors in card creation
        if "error" in response:
            error_enum = PaymeErrorCode.get_error_enum(response["error"]["code"])
            logger.error(
                "❌ Error creating card: %s - %s",
                error_enum,
                response["error"]["message"],
            )
            return

        # If card creation is successful, get the token and send SMS code
        token = response["result"]["card"]["token"]
        response = await payme_client.get_card_verify_code(token)
        print("Response after requesting SMS code:", response)  # Debugging output
        phone = response["result"]["phone"]

        logger.info("✅ Card created. Token: %s", token)
        logger.info("📲 SMS sent to: %s", phone)

        # Step 2️⃣ Get verify code (usually this is separate API call after user submits SMS code)
        logger.info("2️⃣ Verifying card...")
        SMS_CODE = input(
            f"Enter SMS code sent to {phone} "
            f"(sandbox always accepts {SMS_VERIFY_CODE}): "
        ).strip()
        verify = await payme_client.verify_card(code=SMS_CODE, token=token)

        if "error" in verify:
            error_enum = PaymeErrorCode.get_error_enum(verify["error"]["code"])
            logger.error(
                "❌ Error verifying card: %s - %s",
                error_enum,
                verify["error"]["message"],
            )
            return

        token_response = verify["result"]["card"]["token"]
        logger.info("✅ Card verified. Updated token: %s", token_response)

        # Step 3️⃣ Transaction
        logger.info("3️⃣ Creating transaction...")

        amount = COURSE_PRICE * 100  # Payme API uses "tiyin", so multiply by 100

        # Create receipt
        receipt_response = await payme_client.create_receipt(
            order_id=str(USER_ID),
            amount=Decimal(amount),
            # order_type="course_payment"  # Example order type
        )
        # Check for error
        if "error" in receipt_response:
            error_enum = PaymeErrorCode.get_error_enum(
                receipt_response["error"]["code"]
            )
            logger.error(
                "❌ Error creating receipt: %s - %s",
                error_enum,
                receipt_response["error"]["message"],
            )
            return
        receipt_id = receipt_response["result"]["receipt"]["_id"]
        logger.info("Receipt created with ID: %s", receipt_id)

        # Pay receipt
        pay_response = await payme_client.pay_receipt(receipt_id, token)

        if "error" in pay_response:
            error_enum = PaymeErrorCode.get_error_enum(pay_response["error"]["code"])
            logger.error(
                "❌ Error in transaction: %s - %s",
                error_enum,
                pay_response["error"]["message"],
            )
        else:
            paid_amount = pay_response["result"]["receipt"]["amount"]
            logger.info(
                "✅ Transaction successful! Amount paid: %.2f so'm", paid_amount / 100
            )

        logger.info("=== Example finished ===")
    except Exception:
        logger.exception("❌ An error occurred")
    finally:
        await payme_client.close()


if __name__ == "__main__":
    asyncio.run(main())
