from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, Field


class AuthResponse(BaseModel):
    """
    Represents the OAuth response returned by Comdirect during authentication.
    Automatically calculates the 'expires_at' datetime when initialized.
    """

    access_token: str
    refresh_token: str
    expires_in: int
    scope: Optional[str] = None
    kdnr: Optional[str] = None
    bpid: Optional[str] = None
    kontaktId: Optional[str] = Field(None, alias="kontaktId")

    # Computed field (not in the Comdirect API response)
    @property
    def expires_at(self) -> datetime:
        """Calculate the exact expiration datetime based on 'expires_in'."""
        return datetime.now(timezone.utc) + timedelta(seconds=self.expires_in - 30)


class TokenState(BaseModel):
    """
    Holds the currently active token and metadata between API calls.
    This is shared across all subclients (auth, sessions, banking, brokerage).
    """

    primary_access_token: Optional[str] = None
    session_access_token: Optional[str] = None
    banking_access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[float] = None  # epoch timestamp
    kdnr: Optional[str] = None
    bpid: Optional[str] = None
    kontaktid: Optional[str] = Field(None, alias="kontaktId")

    def update_from_auth(self, auth: AuthResponse):
        """Update token state after authentication or token refresh."""
        self.primary_access_token = auth.access_token
        self.refresh_token = auth.refresh_token
        self.token_expires_at = auth.expires_at.timestamp()
        self.kdnr = auth.kdnr
        self.bpid = auth.bpid
        self.kontaktid = auth.kontaktId
