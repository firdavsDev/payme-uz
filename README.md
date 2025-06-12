# Payme API Client

This package provides a clean, testable, production-ready asynchronous Payme API client for Python (Django or any ASGI/async app).

✅ SOLID  
✅ DRY  
✅ Type-safe (with `PaymeErrorCode` enum)  
✅ Built-in retries + logging  
✅ Gracefully closes aiohttp session  
✅ Unit-test ready

---

## Structure
```

payme/
├── __init__.py
├── enums.py          # PaymeErrorCode enum
├── client.py         # Low-level PaymeAPIClient
├── service.py        # High-level PaymeService (easy to use in app)
└── tests/            # Unit tests
└── test\_payme\_client.py
└── test\_payme\_service.py

```

---

## Installation

```

pip install -r requirements.txt

```

---

## Usage

### Service example

```bash
pip install payme-uz
```

```python

from payme.client import PaymeAPIClient
from payme.enums import PaymeErrorCode
from payme.service import PaymeService

CARD_NUMBER = "8600123456789012"
CARD_EXPIRE = "2504"  # MMYY
COURSE_PRICE = 1000  # so'm
RETURN_URL = "https://yourapp.com/return"

USER_ID = 12345  # Example user ID

#===================================================

# Step 1️⃣ Create card
print("\n1️⃣ Creating card...")
payme_client = PaymeAPIClient()
response = await payme_client.create_card(CARD_NUMBER, CARD_EXPIRE, save=False)

#===================================================

# Get the token and send SMS code
token = response["result"]["card"]["token"]
response = await payme_client.get_card_verify_code(token)
phone = response["result"]["phone"]

print(f"✅ Card created. Token: {token}")
print(f"📲 SMS sent to: {phone}")

#===================================================

# Step 2️⃣ Get verify code (usually this is separate API call after user submits SMS code)
print("\n2️⃣ Verifying card...")
SMS_CODE = input(f"Enter SMS code sent to {phone}: ").strip()
verify = await payme_client.verify_card(code=SMS_CODE, token=token)
token_response = verify["result"]["card"]["token"]

#===================================================

# Step 3️⃣ Transaction
print("\n3️⃣ Creating transaction...")
payme_service = PaymeService()

amount = COURSE_PRICE * 100  # Payme API uses "tiyin", so multiply by 100

result = await payme_service.create_and_pay_transaction(
    token=token_response,
    order_id=str(USER_ID),
    amount=Decimal(amount),
)
paid_amount = result["result"]["receipt"]["amount"]
print(f"✅ Transaction successful! Amount paid: {paid_amount / 100:.2f} so'm")

#===================================================

# Step 4️⃣ Close sessions
await payme_client.close()
await payme_service.close()

# open /examples/example.py

```

---

## Testing

```bash
pytest tests -v
pytest --cov=payme --cov-report=term-missing tests/ -v
pytest --cov=payme --cov-report=html tests/ -v
open htmlcov/index.html

```

## Environment variables

You must define PAYME_SETTINGS in your environment, e.g. using a `.env` file:

```.env
# Set to "true" for production, "false" for test environment
PAYME_ENV=false

# Your Payme API token
PAYME_TOKEN=your_payme_token_here

# Your Payme secret key
PAYME_SECRET_KEY=your_secret_key_here

# Account keys (used for receipts)
PAYME_ACCOUNT_KEY_1=your_account_key_1
PAYME_ACCOUNT_KEY_2=order_type

```

---

## Notes

* Built-in retry logic with 10 attempts for network errors.
* Built-in timeout (10 seconds by default).
* All responses are logged.
* Session is reusable — you must call `close()` when done.
* You can inject your own `aiohttp.ClientSession` for advanced use cases or testing.

---

![Python Tests](https://github.com/firdavsdev/payme-client/actions/workflows/python-tests.yml/badge.svg)
