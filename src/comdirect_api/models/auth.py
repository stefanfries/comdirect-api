from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import field_validator

from .base import ComdirectBaseModel


class AuthResponse(ComdirectBaseModel):
    """
    Represents the OAuth response returned by Comdirect during authentication.
    Automatically calculates the 'expires_at' datetime when initialized.
    """

    access_token: str
    refresh_token: str
    expires_in: int
    scope: str | None = None
    kdnr: str | None = None
    bpid: str | None = None
    kontakt_id: str | None = None

    @field_validator("kdnr", "bpid", "kontakt_id", mode="before")
    @classmethod
    def convert_to_string(cls, v):
        """Convert integer IDs to strings if needed."""
        if v is not None and not isinstance(v, str):
            return str(v)
        return v

    # Computed field (not in the Comdirect API response)
    @property
    def expires_at(self) -> datetime:
        """Calculate the exact expiration datetime based on 'expires_in'."""
        return datetime.now(UTC) + timedelta(seconds=self.expires_in - 30)


class TokenState(ComdirectBaseModel):
    """
    Holds the currently active token and metadata between API calls.
    This is shared across all subclients (auth, sessions, banking, brokerage).
    """

    primary_access_token: str | None = None
    session_access_token: str | None = None
    banking_access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: float | None = None  # epoch timestamp
    kdnr: str | None = None
    bpid: str | None = None
    kontakt_id: str | None = None

    def update_from_auth(self, auth: AuthResponse):
        """Update token state after authentication or token refresh."""
        self.primary_access_token = auth.access_token
        self.refresh_token = auth.refresh_token
        self.token_expires_at = auth.expires_at.timestamp()
        self.kdnr = auth.kdnr
        self.bpid = auth.bpid
        self.kontakt_id = auth.kontakt_id
