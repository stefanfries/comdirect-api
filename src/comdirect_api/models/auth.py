from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, Field, model_validator


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
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def compute_expiry(cls, values):  # ignore[no-self-argument]
        """Derive `expires_at` from `expires_in` automatically."""
        now = datetime.now(timezone.utc)
        values.expires_at = now + timedelta(seconds=values.expires_in - 30)
        return values


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
    kontaktId: Optional[str] = Field(None, alias="kontaktId")

    def update_from_auth(self, auth: AuthResponse):
        """Update token state after authentication or token refresh."""
        self.primary_access_token = auth.access_token
        self.refresh_token = auth.refresh_token
        self.token_expires_at = auth.expires_at.timestamp()
        self.kdnr = auth.kdnr
        self.bpid = auth.bpid
        self.kontaktid = auth.kontaktId

    def is_expired(self, margin_seconds: int = 60) -> bool:
        """Check if the token is expired or close to expiry."""
        if not self.token_expires_at:
            return True
        now = datetime.now(timezone.utc).timestamp()
        return now >= (self.token_expires_at - margin_seconds)
