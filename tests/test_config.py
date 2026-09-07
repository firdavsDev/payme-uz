from dataclasses import FrozenInstanceError

import pytest

from payme.config import PRODUCTION_API_URL, TEST_API_URL, PaymeConfig
from payme.errors import PaymeConfigError


def test_reads_the_environment():
    config = PaymeConfig.from_env()
    assert config.token == "test-token"
    assert config.account_type_key == "order_type"
    assert config.production is False
    assert config.api_url == TEST_API_URL


def test_environment_is_read_per_client_not_at_import(monkeypatch):
    monkeypatch.setenv("PAYME_TOKEN", "changed-after-import")
    assert PaymeConfig.from_env().token == "changed-after-import"


def test_explicit_arguments_win_over_the_environment(monkeypatch):
    monkeypatch.setenv("PAYME_ENV", "true")
    config = PaymeConfig.from_env(token="explicit", production=False)
    assert config.token == "explicit"
    assert config.api_url == TEST_API_URL


def test_production_switch():
    config = PaymeConfig.from_env(production=True)
    assert config.api_url == PRODUCTION_API_URL
    assert config.checkout_url == "https://checkout.paycom.uz"


def test_auth_headers_differ_by_method_group():
    config = PaymeConfig(token="id", secret_key="key")
    assert config.card_auth == {"X-Auth": "id"}
    assert config.receipt_auth == {"X-Auth": "id:key"}


def test_missing_settings_are_named():
    config = PaymeConfig(token="id")
    assert config.missing() == ("PAYME_SECRET_KEY", "PAYME_ACCOUNT_KEY_1")


def test_receipt_auth_refuses_to_send_none():
    config = PaymeConfig(token="id")
    with pytest.raises(PaymeConfigError, match="PAYME_SECRET_KEY"):
        _ = config.receipt_auth


def test_config_is_immutable():
    config = PaymeConfig(token="id")
    with pytest.raises(FrozenInstanceError):
        config.token = "other"  # type: ignore[misc]
