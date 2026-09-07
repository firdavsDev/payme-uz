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

Async-only. `PaymeAPIClient` (`src/payme/client.py`) wraps Payme's JSON-RPC endpoint over `aiohttp`; every public method builds `{"method", "params"}` and goes through `_request_with_retry`, which retries **only** `ClientConnectionError` (10 attempts, 1s fixed sleep). Timeouts and non-200 statuses do not retry — a non-200 is logged as an error and its parsed body returned as if successful.

Two auth groups, distinguished only by the header dict passed: card methods (`create_card`, `get_card_verify_code`, `verify_card`) use `X-Auth: TOKEN`; receipt methods (`create_receipt`, `pay_receipt`, `cancel_receipt`) use `X-Auth: TOKEN:SECRET_KEY`. `create_initialization_link` makes no HTTP call — it base64-encodes a param string against the checkout host.

**Errors are not exceptions.** There are no custom exception classes. Failures come back as `{"error": {"code", "message"}}` that callers must check by hand, mapping the code via `PaymeErrorCode.get_error_enum(code)` (returns `None` for unknown codes).

`src/payme/__init__.py` re-exports `PaymeAPIClient`, `PaymeErrorCode`, `ERROR_DESCRIPTIONS`, and `setup_logger`, so both `from payme import PaymeAPIClient` and `from payme.client import PaymeAPIClient` work.

## Gotchas

- **Amounts are in tiyin** (1/100 so'm) - callers multiply by 100. `create_receipt` and `create_initialization_link` send an integer and raise `ValueError` on a fractional amount rather than truncating.
- **`PaymeErrorCode` has heavy value aliasing** - 62 declared names collapse to 37 members (Python `Enum` semantics). `PaymeErrorCode.CARD_EXPIRED is PaymeErrorCode.SMS_NOT_CONNECTED` is `True`. Do not branch on a specific aliased name; `get_error_enum` can only ever return the first-declared name for a duplicated value, and `description()` lists every meaning a shared code carries.
- **A non-200 response is logged and its body returned as if successful.** Callers must check for an `"error"` key regardless of transport status.
- **Only `ClientConnectionError` is retried** (10 attempts, 1s fixed sleep). Timeouts are deliberately not retried - a retried payment can double-charge.
- **`PAYME_ENV=false` points at `checkout.test.paycom.uz`, which has its own cashbox registry.** A production merchant id gets `-32504 Access denied` with `data: "invalid_id"` there - the same response a made-up id gets - so that error means "this cashbox is unknown on this host", not "bad credentials". Test credentials come from the separate test cabinet at `https://merchant.test.paycom.uz` (login: your phone, password `qwerty`, SMS `666666`), where you create a business and a "Виртуальный терминал" cashbox; its key comes from a Payme technical specialist. This is not the `test.paycom.uz` Merchant API sandbox, which does reuse the production merchant id.
- `payme.testing` holds the documented sandbox cards and `SMS_VERIFY_CODE = "666666"`. They only work against the test host.
- **`-31623` is not a Payme failure - it wraps the error your own Merchant API endpoint returned.** `receipts.create` makes Payme call the endpoint configured on the cashbox (`CheckPerformTransaction`), and the nested `error.data` carries that server's reply. An inner `-32504 "Insufficient privileges"` means your endpoint rejected the `Authorization: Basic base64("Paycom:<cashbox key>")` header Payme sent. Always read `error["data"]`, not just `error["message"]`.
- A wrong or missing `account` subfield returns `-31610` with `data` naming the expected field, so it is easy to tell apart from the endpoint failure above.
- **Card tokens are bearer credentials** - with the cashbox key they can charge the card. The client masks `token`, `number` and `expire` before logging responses; never print one in full.
- `close()` closes only a session the client created; a session passed into `__init__` belongs to the caller and is left open.

## Conventions

- Target **Python 3.11+** (`requires-python = ">=3.11"`); CI runs 3.11, 3.12 and 3.13.
- **Never use f-strings in logging calls** (ruff `G004`) - pass `%s` placeholders and arguments: `logger.info("[Payme API] %s Response: %s", method, result)`. Inside an `except` block use `logger.exception("...")` **without** interpolating the exception (ruff `TRY401`); the traceback is already attached.
- Intentional `PaymeErrorCode` aliases carry `# noqa: PIE796` with an `# alias of X` note on the line above. Keep both when adding a shared code, and never wrap those lines - black moving the comment breaks the suppression.
- Commit directly to `main`. Free-form sentence-case commit messages ("Update README.md", "Refactor payment process: ..."), not Conventional Commits.
- Line length is not enforced (both linters ignore E501), but black's 88-column default applies to `src/`, `tests/` and `examples/`.
