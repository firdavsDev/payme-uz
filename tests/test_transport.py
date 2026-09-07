import logging

import pytest
from aiohttp import ClientConnectionError
from tests.conftest import FakeSession

from payme.errors import AccessDeniedError, PaymeTransportError
from payme.retry import RetryPolicy
from payme.transport import JsonRpcTransport

URL = "https://checkout.test.paycom.uz/api"


def transport(session, **kwargs) -> JsonRpcTransport:
    return JsonRpcTransport(URL, session=session, **kwargs)


@pytest.mark.asyncio
async def test_returns_the_result_and_frames_the_envelope():
    session = FakeSession({"result": {"ok": True}})

    result = await transport(session).call(
        "cards.check", {"token": "t"}, {"X-Auth": "id"}
    )

    assert result == {"ok": True}
    assert session.last_payload == {
        "id": 1,
        "method": "cards.check",
        "params": {"token": "t"},
    }
    assert session.last_headers == {"X-Auth": "id"}


@pytest.mark.asyncio
async def test_request_ids_increment_per_transport():
    session = FakeSession({"result": {}}, {"result": {}})
    t = transport(session)

    await t.call("cards.check", {}, {})
    await t.call("cards.check", {}, {})

    assert [call["json"]["id"] for call in session.calls] == [1, 2]


@pytest.mark.asyncio
async def test_error_objects_raise():
    session = FakeSession({"error": {"code": -32504, "message": "Access denied."}})

    with pytest.raises(AccessDeniedError) as excinfo:
        await transport(session).call("cards.create", {}, {})

    assert excinfo.value.method == "cards.create"


@pytest.mark.asyncio
async def test_non_json_body_becomes_a_transport_error():
    session = FakeSession((502, ValueError("not json")))

    with pytest.raises(PaymeTransportError, match="non-JSON"):
        await transport(session).call("cards.check", {}, {})


@pytest.mark.asyncio
async def test_connection_errors_retry_only_when_the_call_opted_in(mocker):
    mocker.patch("payme.retry.asyncio.sleep")
    session = FakeSession(ClientConnectionError("boom"), {"result": {"ok": True}})

    result = await transport(session, retry_policy=RetryPolicy(attempts=3)).call(
        "cards.check", {}, {}, retry=True
    )

    assert result == {"ok": True}
    assert len(session.calls) == 2


@pytest.mark.asyncio
async def test_money_moving_calls_are_never_replayed():
    session = FakeSession(ClientConnectionError("boom"), {"result": {"paid": True}})

    with pytest.raises(ClientConnectionError):
        await transport(session).call("receipts.pay", {}, {})  # retry defaults to False

    assert len(session.calls) == 1, "a failed payment must not be retried"


@pytest.mark.asyncio
async def test_retries_give_up_and_raise_the_last_error(mocker):
    mocker.patch("payme.retry.asyncio.sleep")
    session = FakeSession(*[ClientConnectionError("boom")] * 5)

    with pytest.raises(ClientConnectionError):
        await transport(session, retry_policy=RetryPolicy(attempts=3)).call(
            "cards.check", {}, {}, retry=True
        )

    assert len(session.calls) == 3


@pytest.mark.asyncio
async def test_card_data_is_masked_in_logs(caplog):
    token = "6a9f0044" + "s" * 200
    session = FakeSession({"result": {"card": {"token": token}}})

    with caplog.at_level(logging.INFO, logger="payme.transport"):
        result = await transport(session).call("cards.create", {}, {})

    assert result["card"]["token"] == token, "the caller still gets the real token"
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert token not in logged
    assert "6a9f0044...(208 chars)" in logged


@pytest.mark.asyncio
async def test_an_injected_session_is_left_open():
    session = FakeSession()
    t = transport(session)

    await t.close()

    assert not session.closed


@pytest.mark.asyncio
async def test_no_session_is_created_before_the_first_call():
    t = JsonRpcTransport(URL)
    assert t.session is None
    await t.close()
