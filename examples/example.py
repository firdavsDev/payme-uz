import asyncio
from decimal import Decimal

from payme.client import PaymeAPIClient
from payme.enums import PaymeErrorCode

# Example params (replace these with real values for your test)
CARD_NUMBER = "8600123456789012"
CARD_EXPIRE = "2504"  # MMYY
COURSE_PRICE = 1000  # so'm
RETURN_URL = "https://yourapp.com/return"

USER_ID = 12345  # Example user ID


async def main():
    print("=== Payme Example ===")

    # Step 1️⃣ Create card
    print("\n1️⃣ Creating card...")
    payme_client = PaymeAPIClient()
    response = await payme_client.create_card(CARD_NUMBER, CARD_EXPIRE, save=False)

    # Check for errors in card creation
    if "error" in response:
        error_enum = PaymeErrorCode.get_error_enum(response["error"]["code"])
        print(f"❌ Error creating card: {error_enum} - {response['error']['message']}")
        await payme_client.close()
        return

    # If card creation is successful, get the token and send SMS code
    token = response["result"]["card"]["token"]
    response = await payme_client.get_card_verify_code(token)
    phone = response["result"]["phone"]

    print(f"✅ Card created. Token: {token}")
    print(f"📲 SMS sent to: {phone}")

    # Step 2️⃣ Get verify code (usually this is separate API call after user submits SMS code)
    print("\n2️⃣ Verifying card...")
    SMS_CODE = input(f"Enter SMS code sent to {phone}: ").strip()
    verify = await payme_client.verify_card(code=SMS_CODE, token=token)

    if "error" in verify:
        error_enum = PaymeErrorCode.get_error_enum(verify["error"]["code"])
        print(f"❌ Error verifying card: {error_enum} - {verify['error']['message']}")
        await payme_client.close()
        return

    token_response = verify["result"]["card"]["token"]
    print(f"✅ Card verified. Updated token: {token_response}")

    # Step 3️⃣ Transaction
    print("\n3️⃣ Creating transaction...")

    amount = COURSE_PRICE * 100  # Payme API uses "tiyin", so multiply by 100

    result = await payme_client.create_and_pay_transaction(
        token=token_response,
        order_id=str(USER_ID),
        amount=Decimal(amount),
    )

    if "error" in result:
        error_enum = PaymeErrorCode.get_error_enum(result["error"]["code"])
        print(f"❌ Error in transaction: {error_enum} - {result['error']['message']}")
    else:
        paid_amount = result["result"]["receipt"]["amount"]
        print(f"✅ Transaction successful! Amount paid: {paid_amount / 100:.2f} so'm")

    # Step 4️⃣ Close sessions
    await payme_client.close()

    print("\n=== Example finished ===")


if __name__ == "__main__":
    asyncio.run(main())
