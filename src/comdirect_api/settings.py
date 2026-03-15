from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClientSettings(BaseSettings):
    """
    Load Settings for Comdirect API credentials from .env file.
    """

    client_id: SecretStr
    client_secret: SecretStr
    zugangsnummer: SecretStr
    pin: SecretStr

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = ClientSettings()
