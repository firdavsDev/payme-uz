import logging
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
            "id": 1,
            "method": "receipts.create",
            "params": {"amount": 100000, "account": {"order_id": "123"}},
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


@pytest.mark.asyncio
async def test_order_type_is_sent_only_when_set(mocker):
    client = PaymeAPIClient()
    try:
        patched = mock_post(mocker, client, {"result": {}})

        await client.create_receipt(
            order_id="123", amount=Decimal(100000), order_type="course"
        )

        account = patched.call_args.kwargs["json"]["params"]["account"]
        assert account == {"order_id": "123", "order_type": "course"}
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_each_request_carries_an_incrementing_envelope_id(mocker):
    client = PaymeAPIClient()
    try:
        patched = mock_post(mocker, client, {"result": {}})

        await client.cancel_receipt(receipt_id="a")
        await client.cancel_receipt(receipt_id="b")

        ids = [call.kwargs["json"]["id"] for call in patched.call_args_list]
        assert ids == [1, 2]
    finally:
        await client.close()


# RUN: pytest tests -v


@pytest.mark.asyncio
async def test_card_token_is_masked_in_logs(mocker, caplog):
    client = PaymeAPIClient()
    try:
        token = "6a9f004412293db317bb151b_" + "s" * 200
        mock_post(mocker, client, {"result": {"card": {"token": token}}})

        with caplog.at_level(logging.INFO, logger="payme.client"):
            response = await client.create_card(card_number="8600", expire="0399")

        # The caller still gets the real token; only the log line is masked.
        assert response["result"]["card"]["token"] == token
        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert token not in logged
        assert "6a9f0044...(225 chars)" in logged
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_check_and_remove_card_use_card_auth(mocker):
    client = PaymeAPIClient()
    try:
        patched = mock_post(mocker, client, {"result": {"success": True}})

        await client.check_card(token="tok")
        await client.remove_card(token="tok")

        methods = [call.kwargs["json"]["method"] for call in patched.call_args_list]
        assert methods == ["cards.check", "cards.remove"]
        for call in patched.call_args_list:
            assert call.kwargs["headers"] == {"X-Auth": "test-token"}
            assert call.kwargs["json"]["params"] == {"token": "tok"}
    finally:
        await client.close()
