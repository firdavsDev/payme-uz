import pytest
from decimal import Decimal

from payme.service import PaymeService


@pytest.mark.asyncio
async def test_create_and_pay_transaction_success(mocker):
    # Mock PaymeAPIClient inside PaymeService
    mock_client_class = mocker.patch("payme.service.PaymeAPIClient", autospec=True)
    mock_client_instance = mock_client_class.return_value

    # Mock create_receipt
    mock_client_instance.create_receipt.return_value = {
        "result": {"receipt": {"_id": "mock_receipt_id"}}
    }

    # Mock pay_receipt
    mock_client_instance.pay_receipt.return_value = {
        "result": {"receipt": {"amount": 100000}}
    }

    service = PaymeService()

    result = await service.create_and_pay_transaction(
        token="test_token",
        order_id="12345",
        amount=Decimal("100000"),
        order_type="subscription",
    )

    # Assertions
    assert "result" in result
    assert result["result"]["receipt"]["amount"] == 100000

    # Verify mocks called
    mock_client_instance.create_receipt.assert_called_once_with(
        "12345", Decimal("100000"), "subscription"
    )
    mock_client_instance.pay_receipt.assert_called_once_with(
        "mock_receipt_id", "test_token"
    )

    await service.close()


@pytest.mark.asyncio
async def test_create_and_pay_transaction_error_in_create_receipt(mocker):
    mock_client_class = mocker.patch("payme.service.PaymeAPIClient", autospec=True)
    mock_client_instance = mock_client_class.return_value

    # Simulate error in create_receipt
    mock_client_instance.create_receipt.return_value = {
        "error": {"code": -31001, "message": "Invalid amount"}
    }

    service = PaymeService()

    result = await service.create_and_pay_transaction(
        token="test_token",
        order_id="12345",
        amount=Decimal("100000"),
        order_type="subscription",
    )

    # Assertions
    assert "error" in result
    assert result["error"]["code"] == -31001

    mock_client_instance.create_receipt.assert_called_once()
    mock_client_instance.pay_receipt.assert_not_called()

    await service.close()


@pytest.mark.asyncio
async def test_create_payment_link(mocker):
    mock_client_class = mocker.patch("payme.service.PaymeAPIClient", autospec=True)
    mock_client_instance = mock_client_class.return_value

    # Mock create_initialization_link
    mock_client_instance.create_initialization_link.return_value = (
        "https://mock-link.com"
    )

    service = PaymeService()

    link = await service.create_payment_link(
        amount=Decimal("100000"),
        order_id="order123",
        return_url="https://yourapp.com/callback",
        order_type="subscription",
    )

    assert link == "https://mock-link.com"

    mock_client_instance.create_initialization_link.assert_called_once_with(
        Decimal("100000"), "order123", "https://yourapp.com/callback", "subscription"
    )

    await service.close()


# pytest --cov=payme --cov-report=term-missing tests/ -v
