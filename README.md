# Payme API Client

Asynchronous client for the Payme (Paycom) **Subscribe API** — card tokenization,
verification, receipts and payments — for Python 3.11+ (Django, FastAPI, or any
async app).

✅ One responsibility per module — config, transport, retry, validation, errors
✅ Typed exceptions instead of dictionaries you must remember to check
✅ Retries that never replay a payment
✅ Card tokens masked in logs
✅ Pooled connections, injectable session and transport

---

## Structure

```
src/payme
├── __init__.py      # public exports
├── client.py        # PaymeAPIClient: composes config + transport + namespaces
├── config.py        # PaymeConfig: settings, hosts, auth headers
├── transport.py     # JsonRpcTransport: sends calls, raises typed errors
├── retry.py         # RetryPolicy: exponential backoff with jitter
├── cards.py         # client.cards.*
├── receipts.py      # client.receipts.*
├── checkout.py      # hosted-checkout link builder (no HTTP)
├── errors.py        # PaymeError hierarchy
├── enums.py         # PaymeErrorCode + descriptions
├── validation.py    # amount and card normalization
├── redaction.py     # secret masking for logs
├── testing.py       # documented sandbox cards
└── log.py           # optional logger setup
```

---

## Installation

```bash
pip install payme-uz          # soon to be available
```

From source:

```bash
git clone git@github.com:firdavsDev/payme-uz.git
cd payme-uz
pip install -r requirements-dev.txt
pip install -e .
```

---

## Usage

```python
import asyncio
from payme import PaymeAPIClient, PaymeAPIError, MerchantEndpointError

async def charge_user(order_id: str, price_sum: int) -> dict:
    async with PaymeAPIClient() as client:
        card = await client.cards.create("8600 0691 9540 6311", "10/27")
        token = card["card"]["token"]

        await client.cards.get_verify_code(token)
        verified = await client.cards.verify(token, code="666666")
        token = verified["card"]["token"]

        # Payme works in tiyin: 1 so'm = 100 tiyin.
        receipt = await client.receipts.create(order_id=order_id, amount=price_sum * 100)
        return await client.receipts.pay(receipt["receipt"]["_id"], token)

asyncio.run(charge_user("42", 1000))
```

Methods return the JSON-RPC `result` and raise on failure:

```python
try:
    await client.receipts.pay(receipt_id, token)
except MerchantEndpointError as e:
    # Payme called YOUR Merchant API endpoint and it answered with an error.
    log.error("our endpoint refused Payme: %s", e.endpoint_error)
except PaymeAPIError as e:
    log.error("payme error %s: %s (%s)", e.code, e, e.description)
```

Exception classes: `PaymeError` → `PaymeConfigError`, `PaymeTransportError`,
and `PaymeAPIError` → `AccessDeniedError`, `ProtocolError`, `CardError`,
`VerificationError`, `ReceiptError`, `AccountFieldError`, `MerchantEndpointError`.
Every `PaymeAPIError` carries `.code`, `.data`, `.error_code` (the
`PaymeErrorCode` enum member) and `.description`.

The flat methods (`create_card`, `pay_receipt`, …) still exist as aliases of the
namespaced ones.

### Hosted checkout link

```python
client.checkout_link(order_id="42", amount=100_000, return_url="https://app.uz/done")
```

### Configuration

Settings come from the environment, or explicitly — useful when one process
serves several cashboxes:

```python
from payme import PaymeAPIClient, PaymeConfig, RetryPolicy

client = PaymeAPIClient(
    config=PaymeConfig(token="...", secret_key="...", account_key="order_id", production=True),
    retry_policy=RetryPolicy(attempts=5, base_delay=0.25),
)
```

---

## Environment variables

```.env
# "true" selects production (live money); anything else selects the test host
PAYME_ENV=false

PAYME_TOKEN=your_cashbox_id
PAYME_SECRET_KEY=your_cashbox_key
PAYME_ACCOUNT_KEY_1=order_id
PAYME_ACCOUNT_KEY_2=order_type

# Optional: where setup_logger writes payme.log (default: ./logs)
PAYME_LOG_DIR=logs
```

---

## Testing

```bash
make test                                      # with coverage
pytest tests -v
pytest --cov=payme --cov-report=html tests/    # then open htmlcov/index.html
make lint                                      # flake8 + ruff
make format                                    # black + ruff --fix
```

`payme.testing` carries the documented sandbox cards (`CARD_BLOCKED`,
`CARD_EXPIRED`, `CARD_SLOW_THEN_ERROR`, …) and `SMS_VERIFY_CODE`. They only
work against `checkout.test.paycom.uz`, which needs a cashbox Payme registered
on the test host — a production cashbox id is answered there with
`-32504 / invalid_id`.

---

## Notes

* **Retries are opt-in per call.** Only read-only calls (`cards.check`,
  `cards.remove`) retry, on connection errors, with exponential backoff and
  jitter. `receipts.pay` is never replayed — a retried payment can double-charge.
* Timeout is 30s total / 5s connect by default; pass `timeout=` to change it.
* The session is created on first use and pooled; a session you pass in is
  yours to close, one the client made is closed by `close()` or `async with`.
* Card tokens, numbers and expiries are masked before anything is logged.
* Amounts are in **tiyin** and must be whole; a fractional amount raises
  `ValueError` rather than losing precision.

---

![Python Tests](https://github.com/firdavsdev/payme-uz/actions/workflows/python-tests.yml/badge.svg)
