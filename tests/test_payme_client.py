from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientConnectionError, ClientSession

from payme.client import PaymeAPIClient
from payme.enums import PaymeErrorCode


@pytest.fixture(autouse=True)
def payme_env(monkeypatch):
    """Client config is read in __init__, so env vars can be set per test."""
    monkeypatch.setenv("PAYME_ENV", "false")
    monkeypatch.setenv("PAYME_TOKEN", "test-token")
    monkeypatch.setenv("PAYME_SECRET_KEY", "test-secret")
    monkeypatch.setenv("PAYME_ACCOUNT_KEY_1", "order_id")
    monkeypatch.setenv("PAYME_ACCOUNT_KEY_2", "order_type")


def mock_post(mocker, client, payload, status=200):
    """Patch client.session.post to yield `payload` from its context manager."""
    patched = mocker.patch.object(client.session, "post", autospec=True)
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value.json.return_value = payload
    mock_cm.__aenter__.return_value.status = status
    patched.return_value = mock_cm
    return patched


@pytest.mark.asyncio
async def test_create_receipt_success(mocker):
    client = PaymeAPIClient()
    try:
        patched = mock_post(
            mocker, client, {"result": {"receipt": {"_id": "mock_receipt_id"}}}
        )

        response = await client.create_receipt(order_id="123", amount=Decimal(100000))

        assert response["result"]["receipt"]["_id"] == "mock_receipt_id"

        sent = patched.call_args.kwargs
        assert sent["url"] == PaymeAPIClient.TEST_URL
        assert sent["json"] == {
            "method": "receipts.create",
            "params": {
                "amount": 100000,
                "account": {"order_id": "123", "order_type": None},
            },
        }
        # Receipt methods authenticate with TOKEN:SECRET_KEY.
        assert sent["headers"] == {"X-Auth": "test-token:test-secret"}
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_create_receipt_error(mocker):
    client = PaymeAPIClient()
    try:
        mock_post(
            mocker,
            client,
            {
                "error": {
                    "code": PaymeErrorCode.INVALID_AMOUNT.value,
                    "message": "Invalid amount",
                }
            },
        )

        response = await client.create_receipt(order_id="123", amount=Decimal(100000))

        # Errors come back as data, not exceptions.
        assert response["error"]["code"] == PaymeErrorCode.INVALID_AMOUNT.value
        assert response["error"]["message"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_create_receipt_rejects_fractional_amount(mocker):
    client = PaymeAPIClient()
    try:
        patched = mock_post(mocker, client, {"result": {}})

        with pytest.raises(ValueError, match="whole number of tiyin"):
            await client.create_receipt(order_id="123", amount=Decimal("100.5"))

        patched.assert_not_called()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_card_methods_use_token_only_auth(mocker):
    client = PaymeAPIClient()
    try:
        patched = mock_post(mocker, client, {"result": {"card": {"token": "tok"}}})

        await client.create_card(card_number="8600...", expire="12/99", save=True)

        assert patched.call_args.kwargs["headers"] == {"X-Auth": "test-token"}
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_card_verify_code_does_not_mutate_response(mocker):
    client = PaymeAPIClient()
    try:
        payload = {"result": {"sent": True}}
        mock_post(mocker, client, payload)

        response = await client.get_card_verify_code(token="tok")

        assert response["token"] == "tok"
        assert "token" not in payload, "API response must not be mutated in place"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_retries_on_connection_error(mocker):
    client = PaymeAPIClient()
    try:
        sleep = mocker.patch("payme.client.asyncio.sleep", new_callable=AsyncMock)
        patched = mock_post(mocker, client, {"result": {"ok": True}})
        success_cm = patched.return_value
        patched.side_effect = [ClientConnectionError("boom"), success_cm]

        response = await client.cancel_receipt(receipt_id="abc")

        assert response == {"result": {"ok": True}}
        assert patched.call_count == 2
        sleep.assert_awaited_once_with(1)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_config_falls_back_to_env_and_can_be_overridden(monkeypatch):
    monkeypatch.setenv("PAYME_ENV", "true")
    production_client = PaymeAPIClient()
    try:
        assert production_client.production is True
        assert production_client.url == PaymeAPIClient.PRODUCTION_URL
    finally:
        await production_client.close()

    override = PaymeAPIClient(token="explicit", production=False)
    try:
        assert override.token == "explicit"
        assert override.url == PaymeAPIClient.TEST_URL
    finally:
        await override.close()


@pytest.mark.asyncio
async def test_close_closes_own_session_but_not_an_injected_one():
    own = PaymeAPIClient()
    await own.close()
    assert own.session.closed

    injected = ClientSession()
    try:
        client = PaymeAPIClient(session=injected)
        await client.close()
        assert not injected.closed, "an injected session belongs to the caller"
    finally:
        await injected.close()


# RUN: pytest tests -v
