"""Client settings, resolved once and then immutable."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .errors import PaymeConfigError

TEST_API_URL = "https://checkout.test.paycom.uz/api"
PRODUCTION_API_URL = "https://checkout.paycom.uz/api"
TEST_CHECKOUT_URL = "https://checkout.test.paycom.uz"
PRODUCTION_CHECKOUT_URL = "https://checkout.paycom.uz"

DEFAULT_TIMEOUT = 30.0


@dataclass(frozen=True)
class PaymeConfig:
    """Everything the client needs to talk to one cashbox.

    Build it with :meth:`from_env` to read the documented environment
    variables, or construct it directly to keep configuration out of the
    process environment entirely.
    """

    token: str | None = None
    secret_key: str | None = None
    account_key: str | None = None
    account_type_key: str = "order_type"
    production: bool = False
    timeout: float = DEFAULT_TIMEOUT

    @classmethod
    def from_env(
        cls,
        *,
        token: str | None = None,
        secret_key: str | None = None,
        account_key: str | None = None,
        account_type_key: str | None = None,
        production: bool | None = None,
        timeout: float | None = None,
        load_env_file: bool = True,
    ) -> PaymeConfig:
        """Read settings from the environment; explicit arguments win.

        ``.env`` is loaded here rather than at import, so a test or a caller
        that sets ``os.environ`` after importing the package still wins.
        """
        if load_env_file:
            load_dotenv()
        return cls(
            token=token if token is not None else os.getenv("PAYME_TOKEN"),
            secret_key=(
                secret_key if secret_key is not None else os.getenv("PAYME_SECRET_KEY")
            ),
            account_key=(
                account_key
                if account_key is not None
                else os.getenv("PAYME_ACCOUNT_KEY_1")
            ),
            account_type_key=(
                account_type_key
                if account_type_key is not None
                else os.getenv("PAYME_ACCOUNT_KEY_2", "order_type")
            ),
            production=(
                production
                if production is not None
                else os.getenv("PAYME_ENV", "false").lower() == "true"
            ),
            timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
        )

    @property
    def api_url(self) -> str:
        return PRODUCTION_API_URL if self.production else TEST_API_URL

    @property
    def checkout_url(self) -> str:
        return PRODUCTION_CHECKOUT_URL if self.production else TEST_CHECKOUT_URL

    @property
    def card_auth(self) -> dict[str, str]:
        """Card methods authenticate with the cashbox id alone."""
        self.require("token")
        return {"X-Auth": self.token or ""}

    @property
    def receipt_auth(self) -> dict[str, str]:
        """Receipt methods authenticate with ``id:key``."""
        self.require("token", "secret_key")
        return {"X-Auth": f"{self.token}:{self.secret_key}"}

    def missing(self) -> tuple[str, ...]:
        """Names of the settings that are unset, as environment variables."""
        env_names = {
            "token": "PAYME_TOKEN",
            "secret_key": "PAYME_SECRET_KEY",
            "account_key": "PAYME_ACCOUNT_KEY_1",
        }
        return tuple(
            env_name
            for field, env_name in env_names.items()
            if not getattr(self, field)
        )

    def require(self, *fields: str) -> None:
        """Raise unless every named setting has a value.

        Failing here beats sending ``{"X-Auth": "None:None"}`` and reading an
        authorization error back.
        """
        env_names = {
            "token": "PAYME_TOKEN",
            "secret_key": "PAYME_SECRET_KEY",
            "account_key": "PAYME_ACCOUNT_KEY_1",
        }
        absent = [env_names.get(f, f) for f in fields if not getattr(self, f)]
        if absent:
            raise PaymeConfigError(f"Missing Payme configuration: {', '.join(absent)}")
