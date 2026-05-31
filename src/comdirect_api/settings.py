from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AccountSettings(BaseModel):
    """Credentials for a single Comdirect bank connection."""

    zugangsnummer: SecretStr
    pin: SecretStr
    display_name: str | None = None  # Optional human-readable label, e.g. "Megatrend Folger"


class ClientSettings(BaseSettings):
    """
    Load Settings for Comdirect API credentials from .env file.

    Accounts are keyed by a human-readable name (e.g. DEPOT11) and loaded
    via env_nested_delimiter="__":
        ACCOUNTS__DEPOT11__ZUGANGSNUMMER = ...
        ACCOUNTS__DEPOT11__PIN = ...
    """

    client_id: SecretStr
    client_secret: SecretStr
    accounts: dict[str, AccountSettings]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )


settings = ClientSettings()
