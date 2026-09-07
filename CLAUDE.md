# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```
make test          # pytest --cov=payme --cov-report=term-missing tests -v
make lint          # flake8 --ignore=E501 + ruff check, over src/ tests/ examples/
make format        # black + ruff check --fix, over src/ tests/ examples/
make run-example   # PYTHONPATH=src python examples/example.py
```

Single test: `pytest tests/test_payme_client.py -k test_name -v`.

`pytest.ini` sets `pythonpath = src`, so tests import the package without installation. Anything else (a scratch script, `python examples/example.py` run by hand) needs `PYTHONPATH=src` or `pip install -e .`.

pytest-asyncio runs in **strict** mode (no `asyncio_mode` in `pytest.ini`) - every async test needs `@pytest.mark.asyncio`. There is no `conftest.py`; `tests/test_payme_client.py` defines an autouse `payme_env` fixture and a `mock_post` helper that patches `client.session.post` with an `AsyncMock` context manager.

Ruff config lives in `[tool.ruff]` in `pyproject.toml`. `E501` is ignored (black owns formatting) and `TRY003` is ignored (no custom exception classes yet). CI runs `ruff check` and `black --check`, so a lint failure fails the build. mypy is a declared dev dependency with no config and no target - it is not enforced.

## Environment

`PaymeAPIClient` reads its configuration in `__init__` (env vars, or keyword overrides: `token`, `secret_key`, `account_key`, `account_type_key`, `production`). `load_dotenv()` still runs at import, but `monkeypatch.setenv` before constructing a client works.

- `PAYME_ENV` - `"true"` selects **production** (`checkout.paycom.uz`, live money); anything else, including unset, selects the test host.
- `PAYME_TOKEN`, `PAYME_SECRET_KEY`, `PAYME_ACCOUNT_KEY_1` - no defaults. Missing values are logged as a warning at construction and then surface as an API authorization error; they are not fatal.
- `PAYME_ACCOUNT_KEY_2` - defaults to `"order_type"`.
- `PAYME_LOG_DIR` - where `setup_logger` writes `payme.log`; defaults to `logs/` under the current working directory.

`.env` is gitignored and populated locally. Never print or commit its contents.

## Architecture

One module per responsibility; `PaymeAPIClient` only composes them.

- `config.py` - `PaymeConfig`, a frozen dataclass. `from_env()` loads `.env` and the `PAYME_*` variables **at call time**, so `monkeypatch.setenv` before constructing a client works. Owns host selection and the two auth headers.
- `transport.py` - `JsonRpcTransport`: numbers the envelope, sends, logs redacted, converts a JSON-RPC `error` into an exception, returns `result`. The session is created lazily on first call (so constructing a client outside a loop is safe) and pooled.
- `retry.py` - `RetryPolicy`: exponential backoff with jitter. **Retry is opt-in per call** (`transport.call(..., retry=True)`); `NO_RETRY` is the default because replaying `receipts.pay` can double-charge.
- `cards.py` / `receipts.py` - `CardsAPI` and `ReceiptsAPI`, reached as `client.cards` / `client.receipts`. Card methods authenticate with the cashbox id, receipt methods with `id:key`.
- `errors.py` - the exception hierarchy plus `exception_for(code)` / `from_error_object(...)`.
- `checkout.py`, `validation.py`, `redaction.py`, `enums.py`, `testing.py`, `log.py` - link building, input normalization, log masking, error codes, sandbox constants, logger setup.

**Failures raise, they are not returned.** Methods return the JSON-RPC `result`; anything else is a `PaymeError` subclass. `PaymeAPIError` carries `.code`, `.data`, `.error_code` (enum) and `.description`.

The flat methods (`create_card`, `pay_receipt`, ...) are one-line aliases of the namespaced ones, kept for existing call sites. Add new behaviour to `CardsAPI`/`ReceiptsAPI`, not to `PaymeAPIClient`.

`src/payme/__init__.py` re-exports the client, config, retry policy, enum and every exception.

## Gotchas

- **Amounts are in tiyin** (1/100 so'm) - callers multiply by 100. `receipts.create` and `checkout_link` send an integer and raise `ValueError` on a fractional amount rather than truncating.
- **`PaymeErrorCode` has heavy value aliasing** - 62 declared names collapse to 37 members (Python `Enum` semantics). `PaymeErrorCode.CARD_EXPIRED is PaymeErrorCode.SMS_NOT_CONNECTED` is `True`. Do not branch on a specific aliased name; `get_error_enum` can only ever return the first-declared name for a duplicated value, and `description()` lists every meaning a shared code carries.
- **A non-200 response is logged at error level but still parsed** - Payme returns JSON-RPC errors with HTTP 200, so status is not the signal; the `error` object is.
- **Only `ClientConnectionError` is retried, and only where a call opts in.** Timeouts are never retried - the server may have processed the request and lost the answer.
- **`PAYME_ENV=false` points at `checkout.test.paycom.uz`, which has its own cashbox registry.** A production merchant id gets `-32504 Access denied` with `data: "invalid_id"` there - the same response a made-up id gets - so that error means "this cashbox is unknown on this host", not "bad credentials". The docs point at a test cabinet on `merchant.test.paycom.uz` to create a "Виртуальный терминал" cashbox, but that host no longer resolves (NXDOMAIN as of 2026-09-07), so Subscribe API test access has to be requested from Payme directly. `test.paycom.uz` is alive but is the Merchant API sandbox ("Sandbox.Paycom.Uz") - a different system, which does reuse the production merchant id.
- `payme.testing` holds the documented sandbox cards and `SMS_VERIFY_CODE = "666666"`. They only work against the test host.
- **`-31623` is not a Payme failure - it wraps the error your own Merchant API endpoint returned.** `receipts.create` makes Payme call the endpoint configured on the cashbox (`CheckPerformTransaction`), and the nested `error.data` carries that server's reply. An inner `-32504 "Insufficient privileges"` means your endpoint rejected the `Authorization: Basic base64("Paycom:<cashbox key>")` header Payme sent. Catch `MerchantEndpointError` and read `.endpoint_error`.
- A wrong or missing `account` subfield returns `-31610` with `data` naming the expected field, so it is easy to tell apart from the endpoint failure above.
- `create_card` normalizes its input: spaces are stripped from the number and `MM/YY` is accepted for the expiry. Sending `"10/27"` or a spaced number straight through returns `-32602 Invalid Params`.
- **Card tokens are bearer credentials** - with the cashbox key they can charge the card. The client masks `token`, `number` and `expire` before logging responses; never print one in full.
- `close()` (and `async with`) closes only a session the client created; a session passed in belongs to the caller.

## Conventions

- Target **Python 3.11+** (`requires-python = ">=3.11"`); CI runs 3.11, 3.12 and 3.13.
- **Never use f-strings in logging calls** (ruff `G004`) - pass `%s` placeholders and arguments: `logger.info("[Payme API] %s Response: %s", method, result)`. Inside an `except` block use `logger.exception("...")` **without** interpolating the exception (ruff `TRY401`); the traceback is already attached.
- Intentional `PaymeErrorCode` aliases carry `# noqa: PIE796` with an `# alias of X` note on the line above. Keep both when adding a shared code, and never wrap those lines - black moving the comment breaks the suppression.
- Commit directly to `main`. Free-form sentence-case commit messages ("Update README.md", "Refactor payment process: ..."), not Conventional Commits.
- Line length is not enforced (both linters ignore E501), but black's 88-column default applies to `src/`, `tests/` and `examples/`.
