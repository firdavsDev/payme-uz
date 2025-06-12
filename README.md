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

.
├── __init__.py
├── examples
│   └── example.py
├── Makefile
├── logs
│   └── payme.log
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── .env.example
├── pytest.ini
├── src
│   └── payme
│       ├── __init__.py
│       ├── enums.py
│       ├── log.py
│       └── client.py
└── tests
    └── test_payme_client.py

```

---

## Installation

## Install via pip (soon to be available)
```bash
pip install payme-uz
```
## Install from source (development version)
```bash
git clone git@github.com:firdavsDev/payme-uz.git
cd payme-uz
pip install -r requirements-dev.txt
pip install -e .
```

---

## Usage

### Service example

```python

from payme.client import PaymeAPIClient
from payme.enums import PaymeErrorCode

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

# Step 3️⃣ Create receipt
print("\n3️⃣ Creating receipt...")

amount = COURSE_PRICE * 100  # Payme API uses "tiyin", so multiply by 100
receipt_response = await payme_client.create_receipt(
    order_id=str(USER_ID),
    amount=Decimal(amount),
    # order_type="course_payment"  # Example order type
)

#===================================================

# Step 4️⃣ Pay receipt
print("\n4️⃣ Paying receipt...")
receipt_id = receipt_response["result"]["receipt"]["_id"]
pay_response = await payme_client.pay_receipt(receipt_id, token)
paid_amount = pay_response["result"]["receipt"]["amount"]
print(f"✅ Transaction successful! Amount paid: {paid_amount / 100:.2f} so'm")

#===================================================

# Step 5️⃣ Close sessions
print("\n5️⃣ Closing Payme client session...")
await payme_client.close()

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

e.g. using a `.env` file:

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
* Built-in timeout (30 seconds by default).
* All responses are logged.
* Session is reusable — you must call `close()` when done.
* You can inject your own `aiohttp.ClientSession` for advanced use cases or testing.

---

![Python Tests](https://github.com/firdavsdev/payme-uz/actions/workflows/python-tests.yml/badge.svg)
