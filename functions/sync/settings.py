from datetime import date, timedelta

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from comdirect_api.settings import ClientSettings


class SyncSettings(ClientSettings):
    """
    Settings for the Comdirect sync function.

    Extends the base Comdirect API credentials with MongoDB Atlas connection details.
    """

    mongodb_connection_string: SecretStr
    mongodb_database: str = "finance"
    depot_transactions_lookback_days: int = 365

    @property
    def depot_transactions_lookback(self) -> str:
        """Earliest booking date (YYYY-MM-DD) for depot transaction fetches."""
        earliest = date.today() - timedelta(days=self.depot_transactions_lookback_days)
        return earliest.isoformat()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = SyncSettings()
