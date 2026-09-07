import base64

import pytest
from tests.conftest import FakeSession

from payme import PaymeAPIClient, PaymeConfig
from payme.config import PRODUCTION_API_URL, TEST_API_URL
from payme.errors import MerchantEndpointError, PaymeConfigError
from payme.testing import CARD_OK
from payme.transport import JsonRpcTransport


def client(session, **kwargs) -> PaymeAPIClient:
    return PaymeAPIClient(session=session, **kwargs)


@pytest.mark.asyncio
async def test_cards_create_normalizes_input_and_uses_card_auth():
    session = FakeSession({"result": {"card": {"token": "tok"}}})

    result = await client(session).cards.create(
        "8600 0691 9540 6311", "10/27", save=True
    )

    assert result == {"card": {"token": "tok"}}
    assert session.last_payload["params"] == {
        "card": {"number": "8600069195406311", "expire": "1027"},
        "save": True,
    }
    assert session.last_headers == {"X-Auth": "test-token"}


@pytest.mark.asyncio
async def test_receipts_create_uses_receipt_auth_and_tiyin():
    session = FakeSession({"result": {"receipt": {"_id": "r1"}}})

    await client(session).receipts.create(order_id="123", amount=100000)

    assert session.last_payload["params"] == {
        "amount": 100000,
        "account": {"order_id": "123"},
    }
    assert session.last_headers == {"X-Auth": "test-token:test-secret"}


@pytest.mark.asyncio
async def test_order_type_is_sent_only_when_given():
    session = FakeSession({"result": {}})

    await client(session).receipts.create("123", 100000, order_type="course")

    assert session.last_payload["params"]["account"] == {
        "order_id": "123",
        "order_type": "course",
    }


@pytest.mark.asyncio
async def test_api_errors_raise_with_the_nested_endpoint_reply():
    session = FakeSession(
        {
            "error": {
                "code": -31623,
                "message": "Сервис поставщика услуг работает некорректно",
                "data": {"code": -32504, "message": {"en": "Insufficient privileges."}},
            }
        }
    )

    with pytest.raises(MerchantEndpointError) as excinfo:
        await client(session).receipts.create("123", 100000)

    assert excinfo.value.endpoint_error["code"] == -32504


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("call_flat", "namespace_method"),
    [
        (lambda c: c.create_card(CARD_OK, "0399"), "cards.create"),
        (lambda c: c.get_card_verify_code("t"), "cards.get_verify_code"),
        (lambda c: c.verify_card("666666", "t"), "cards.verify"),
        (lambda c: c.check_card("t"), "cards.check"),
        (lambda c: c.remove_card("t"), "cards.remove"),
        (lambda c: c.create_receipt("1", 100), "receipts.create"),
        (lambda c: c.pay_receipt("r", "t"), "receipts.pay"),
        (lambda c: c.cancel_receipt("r"), "receipts.cancel"),
    ],
)
async def test_flat_aliases_still_reach_the_right_method(call_flat, namespace_method):
    session = FakeSession({"result": {}})

    await call_flat(client(session))

    assert session.last_payload["method"] == namespace_method


@pytest.mark.asyncio
async def test_verify_card_keeps_its_historical_argument_order():
    session = FakeSession({"result": {}})

    await client(session).verify_card(code="666666", token="tok")

    assert session.last_payload["params"] == {"token": "tok", "code": "666666"}


def test_checkout_link_needs_no_event_loop_or_network():
    link = PaymeAPIClient(
        config=PaymeConfig(token="mid", account_key="order_id")
    ).checkout_link(order_id="42", amount=100000, return_url="https://app.uz/return")

    encoded = link.rsplit("/", 1)[-1]
    assert base64.b64decode(encoded).decode() == (
        "m=mid;ac.order_id=42;a=100000;c=https://app.uz/return"
    )


@pytest.mark.asyncio
async def test_missing_configuration_raises_before_any_request():
    session = FakeSession()
    bare = PaymeAPIClient(session=session, config=PaymeConfig(token="id"))

    # receipts.create needs the account field name before it needs the key.
    with pytest.raises(PaymeConfigError, match="PAYME_ACCOUNT_KEY_1"):
        await bare.receipts.create("1", 100)

    assert session.calls == [], "nothing should have been sent"


def test_production_switch_reaches_the_transport():
    assert PaymeAPIClient(production=True).url == PRODUCTION_API_URL
    assert PaymeAPIClient(production=False).url == TEST_API_URL


@pytest.mark.asyncio
async def test_context_manager_closes_only_its_own_session():
    session = FakeSession({"result": {}})

    async with client(session) as c:
        await c.cards.check("t")

    assert not session.closed


@pytest.mark.asyncio
async def test_a_custom_transport_can_be_injected():
    session = FakeSession({"result": {"ok": True}})
    custom = JsonRpcTransport("https://example.test/api", session=session)

    result = await PaymeAPIClient(transport=custom).cards.check("t")

    assert result == {"ok": True}
    assert session.calls[0]["url"] == "https://example.test/api"
