# payme-uz

Asynchronous client for the Payme (Paycom) **Subscribe API** — card tokenization,
verification, receipts and payments — for Python 3.11+ (Django, FastAPI, or any
async app).

![Python Tests](https://github.com/firdavsdev/payme-uz/actions/workflows/python-tests.yml/badge.svg)

🇺🇿 **Kalitlarni qayerdan olish kerak?** → [docs/KALITLAR.uz.md](docs/KALITLAR.uz.md)
(o'zbekcha qo'llanma: `PAYME_TOKEN`, `PAYME_SECRET_KEY`, `PAYME_ACCOUNT_KEY_1`,
qo'llab-quvvatlashga murojaat namunasi va xatolar jadvali)

---

## Why this client

- **Typed exceptions**, not dictionaries you must remember to inspect.
- **Retries that never replay a payment** — opt-in per call, off by default.
- **Card tokens masked** before anything reaches a log file.
- **Pooled connections**, lazy session, injectable session/transport/config.
- One responsibility per module, so each piece is testable on its own.

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

## Quick start

```python
import asyncio
from payme import PaymeAPIClient

async def charge(order_id: str, price_sum: int) -> dict:
    async with PaymeAPIClient() as client:
        card = await client.cards.create("8600 0691 9540 6311", "10/27")
        token = card["card"]["token"]

        await client.cards.get_verify_code(token)
        verified = await client.cards.verify(token, code="666666")
        token = verified["card"]["token"]

        # Payme works in tiyin: 1 so'm = 100 tiyin.
        receipt = await client.receipts.create(order_id=order_id, amount=price_sum * 100)
        return await client.receipts.pay(receipt["receipt"]["_id"], token)

asyncio.run(charge("42", 1000))
```

Every method returns the JSON-RPC `result` and raises on failure.

---

## API

### `client.cards`

| Method | Payme method | Notes |
|---|---|---|
| `create(number, expire, *, save=False)` | `cards.create` | Spaces and `MM/YY` are normalized for you |
| `get_verify_code(token)` | `cards.get_verify_code` | Sends the SMS |
| `verify(token, code)` | `cards.verify` | Returns the verified token |
| `check(token)` | `cards.check` | Retried on connection errors |
| `remove(token)` | `cards.remove` | Revokes a token immediately |

### `client.receipts`

| Method | Payme method | Notes |
|---|---|---|
| `create(order_id, amount, order_type=None)` | `receipts.create` | `amount` in tiyin, must be whole |
| `pay(receipt_id, token)` | `receipts.pay` | Never retried |
| `cancel(receipt_id)` | `receipts.cancel` | |

### Other

```python
client.checkout_link(order_id="42", amount=100_000, return_url="https://app.uz/done")
```

Builds the hosted-checkout URL. No HTTP call, so it is not a coroutine.

The flat methods — `create_card`, `get_card_verify_code`, `verify_card`,
`check_card`, `remove_card`, `create_receipt`, `pay_receipt`, `cancel_receipt`,
`create_initialization_link` — remain as aliases of the namespaced ones.

---

## Error handling

```python
from payme import MerchantEndpointError, PaymeAPIError

try:
    await client.receipts.pay(receipt_id, token)
except MerchantEndpointError as e:
    # Payme called YOUR Merchant API endpoint and it answered with an error.
    log.error("our endpoint refused Payme: %s", e.endpoint_error)
except PaymeAPIError as e:
    log.error("payme error %s: %s (%s)", e.code, e, e.description)
```

```
PaymeError
├── PaymeConfigError        a setting is missing; raised before any request
├── PaymeTransportError     no usable response (connection dead, body not JSON)
└── PaymeAPIError           Payme returned a JSON-RPC error
    ├── AccessDeniedError       -32504   cashbox unknown on this host
    ├── ProtocolError           JSON-RPC faults: bad request, unknown method
    ├── CardError               blocked, expired, unknown, unsupported card
    ├── VerificationError       wrong, expired or over-attempted SMS code
    ├── AccountFieldError       -31610 and -31050..-31099; `.field` names it
    └── ReceiptError            receipt could not be created, paid or cancelled
        └── MerchantEndpointError  -31623; `.endpoint_error` holds YOUR reply
```

Every `PaymeAPIError` carries `.code`, `.message`, `.data`, `.method`,
`.error_code` (the `PaymeErrorCode` enum member, or `None`) and `.description`
(every meaning the code can carry — Payme reuses codes).

---

## Configuration

Settings are read per client, so changing the environment after import works:

```env
# "true" selects production (live money); anything else selects the test host
PAYME_ENV=false

PAYME_TOKEN=your_cashbox_id
PAYME_SECRET_KEY=your_cashbox_key
PAYME_ACCOUNT_KEY_1=order_id
PAYME_ACCOUNT_KEY_2=order_type

# Optional: where setup_logger writes payme.log (default: ./logs)
PAYME_LOG_DIR=logs
```

Or explicitly — useful when one process serves several cashboxes:

```python
from payme import PaymeAPIClient, PaymeConfig, RetryPolicy

client = PaymeAPIClient(
    config=PaymeConfig(
        token="...", secret_key="...", account_key="order_id",
        production=True, timeout=15.0,
    ),
    retry_policy=RetryPolicy(attempts=5, base_delay=0.25, max_delay=8.0),
)
```

**Where do these values come from?** Cashbox id and key live in the Payme
Business cabinet under the cashbox's *Настройки → Инструменты разработчика*;
`PAYME_ACCOUNT_KEY_1` is the `account` field name configured on that cashbox.
Step-by-step, in Uzbek: [docs/KALITLAR.uz.md](docs/KALITLAR.uz.md).

---

## Testing against Payme

`payme.testing` carries the documented sandbox cards and the fixed SMS code:

```python
from payme.testing import CARD_BLOCKED, CARD_OK, SMS_VERIFY_CODE, TEST_CARDS
```

`CARD_OK`, `CARD_OK_ALT`, `CARD_SMS_NOT_CONNECTED`, `CARD_EXPIRED`,
`CARD_BLOCKED`, `CARD_SYSTEM_ERROR`, `CARD_SLOW_THEN_ERROR` — all with
expiry `0399`, and `SMS_VERIFY_CODE = "666666"`.

They only work against `checkout.test.paycom.uz`, which keeps **its own cashbox
registry**: a production cashbox id is answered there with
`-32504 / "invalid_id"` — the same reply a made-up id gets. Test access has to
be requested from Payme; see the Uzbek guide for a message template.

---

## Development

```bash
make test        # pytest with coverage
make lint        # flake8 + ruff
make format      # black + ruff --fix
pytest tests -k test_retry -v
```

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

The test suite never touches the network: `tests/conftest.py` provides a
scripted fake session.

---

## Notes

* **Retries are opt-in per call.** Only `cards.check` and `cards.remove` retry,
  on connection errors, with exponential backoff and jitter. `receipts.pay` is
  never replayed — a retried payment can double-charge.
* Timeout is 30s total / 5s connect by default; pass `timeout=` to change it.
* The session is created on first use and pooled. A session you pass in stays
  yours to close; one the client created is closed by `close()` or `async with`.
* Card tokens, numbers and expiries are masked before being logged. A token is
  a bearer credential — with the cashbox key it can charge the card.
* Amounts are in **tiyin** and must be whole; a fractional amount raises
  `ValueError` instead of silently losing precision.
* `-31623` never means Payme is broken — it wraps the error *your* Merchant API
  endpoint returned. Read `MerchantEndpointError.endpoint_error`.
