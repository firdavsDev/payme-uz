import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from payme.client import PaymeAPIClient
from payme.enums import PaymeErrorCode


@pytest.mark.asyncio
async def test_create_receipt_success(mocker):
    client = PaymeAPIClient()

    # Mock response
    mock_response = {"result": {"receipt": {"_id": "mock_receipt_id"}}}

    # Patch aiohttp.ClientSession.post to return mock_response
    mock_post = mocker.patch.object(client.session, "post", autospec=True)

    # aiohttp post returns a context manager, so we need to mock __aenter__
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value.json.return_value = mock_response
    mock_cm.__aenter__.return_value.status = 200
    mock_post.return_value = mock_cm

    response = await client.create_receipt(order_id="123", amount=Decimal("100000"))

    assert "result" in response
    assert response["result"]["receipt"]["_id"] == "mock_receipt_id"

    await client.close()


@pytest.mark.asyncio
async def test_create_receipt_error(mocker):
    client = PaymeAPIClient()

    # Mock error response
    mock_response = {
        "error": {
            "code": PaymeErrorCode.INVALID_AMOUNT.value,
            "message": "Invalid amount",
        }
    }

    mock_post = mocker.patch.object(client.session, "post", autospec=True)

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value.json.return_value = mock_response
    mock_cm.__aenter__.return_value.status = 200
    mock_post.return_value = mock_cm

    response = await client.create_receipt(order_id="123", amount=Decimal("100000"))

    assert "error" in response
    assert response["error"]["code"] == PaymeErrorCode.INVALID_AMOUNT.value
    assert response["error"]["message"]


# RUN: pytest tests -v
