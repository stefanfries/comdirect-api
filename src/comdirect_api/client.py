"""
Comdirect API Client
This module provides an asynchronous client for interacting with the Comdirect REST API.
It supports OAuth2 authentication, session management, TAN (two-factor authentication) validation,
token refreshing, and account balance retrieval.
Classes:
    ComdirectClient: Main client class for Comdirect API operations.
Dependencies:
    - httpx: For asynchronous HTTP requests.
    - asyncio: For asynchronous operations.
    - uuid: For generating unique session/request IDs.
    - time: For token expiration handling.
    - json: For encoding/decoding request and response data.
    - .utils.timestamp: Utility function for generating timestamps.
Usage:
    Instantiate `ComdirectClient` with your client credentials, then use its
    methods to authenticate, manage sessions, validate TANs, refresh tokens,
    and retrieve account balances.

"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import httpx

from .models.accounts import AccountBalances
from .models.auth import AuthResponse
from .models.depots import AccountDepots, DepotPosition, DepotPositions
from .models.instruments import Instruments
from .models.messages import Documents
from .models.transactions import AccountTransactions, DepotTransactions
from .utils import timestamp

logger = logging.getLogger(__name__)


class ComdirectClient:
    """Class to interact with the Comdirect API."""

    BASE_URL = "https://api.comdirect.de/api"
    OAUTH_URL = "https://api.comdirect.de/oauth/token"

    # ==================== INITIALIZATION ====================

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        zugangsnummer: str,
        pin: str,
    ):
        """
        Initialize ComdirectClient with credentials.

        Note: This only stores credentials. Use `await ComdirectClient.create()`
        to get a fully authenticated client ready for API calls.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.zugangsnummer = zugangsnummer
        self.pin = pin
        # OAuth token for session management (scope: TWO_FACTOR)
        self.primary_access_token: str | None = None
        # OAuth token for banking/brokerage (scope: BANKING_RO BROKERAGE_RW SESSION_RW)
        self.banking_access_token: str | None = None
        self.refresh_token: str | None = None
        self.session_id: str | None = (
            None  # session_id will be set after authentication
        )
        self.token_expires_at: float = 0
        self.scope: str | None = None
        self.kdnr: str | None = None  # Kundennummer
        self.bpid: str | None = None  # Interne Identifikationsnummer
        self.kontaktid: str | None = None  # Interne Identifikationsnummer
        self.available_tan_types: list[str] = []
        self.tan_type: str | None = None
        self.session_tan_active: bool = False
        self.activated_2fa: bool = False

        # TAN challenge info, only valid between TAN initiation and activation
        self.challenge_id: str | None = None
        self.challenge_link: str | None = None

    @classmethod
    async def create(
        cls,
        client_id: str | None = None,
        client_secret: str | None = None,
        zugangsnummer: str | None = None,
        pin: str | None = None,
    ) -> "ComdirectClient":
        """Create and authenticate a ComdirectClient instance.

        This factory method handles the complete authentication flow:
        1. Primary OAuth authentication
        2. Session status check
        3. TAN challenge (waits for push notification approval)
        4. Banking/brokerage access token retrieval

        Args:
            client_id: OAuth client ID (defaults to settings.client_id)
            client_secret: OAuth client secret (defaults to settings.client_secret)
            zugangsnummer: Account login number (defaults to settings.zugangsnummer)
            pin: Account PIN (defaults to settings.pin)

        Returns:
            Fully authenticated ComdirectClient ready for API calls.

        Example:
            >>> client = await ComdirectClient.create()
            >>> balances = await client.get_account_balances()
        """
        from .settings import settings

        # Use provided credentials or fall back to settings
        _client_id = client_id or settings.client_id.get_secret_value()
        _client_secret = client_secret or settings.client_secret.get_secret_value()
        _zugangsnummer = zugangsnummer or settings.zugangsnummer.get_secret_value()
        _pin = pin or settings.pin.get_secret_value()

        # Create instance
        instance = cls(
            client_id=_client_id,
            client_secret=_client_secret,
            zugangsnummer=_zugangsnummer,
            pin=_pin,
        )

        # Run complete authentication flow
        await instance._initialize()

        return instance

    async def _initialize(self) -> None:
        """Execute complete authentication flow.

        Private method that orchestrates:
        1. Primary OAuth authentication
        2. Session status retrieval
        3. TAN challenge and validation
        4. Banking/brokerage access token
        """
        logger.info("Authenticating with Comdirect API...")
        await self._authenticate(self.zugangsnummer, self.pin)

        logger.info("Retrieving session status...")
        await self._get_session_status()

        # TAN challenge logs its own progress
        await self._create_validate_session_tan()

        logger.info("Obtaining banking/brokerage access...")
        await self._get_banking_brokerage_access()

        logger.info("Authentication complete! Client ready for API calls.")

    # ==================== PRIVATE HELPERS ====================

    def _request_headers(
        self, token: str, extra: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        base_hdr = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "x-http-request-info": json.dumps(
                {
                    "clientRequestId": {
                        "sessionId": self.session_id,
                        "requestId": timestamp(),
                    }
                }
            ),
            "Content-Type": "application/json",
        }
        if extra:
            base_hdr.update(extra)
        return base_hdr

    # ==================== AUTHENTICATION & SESSION ====================

    async def _authenticate(
        self, username: str, password: str, scope: str = "SESSION_RW"
    ) -> dict[str, Any]:
        """
        Authenticate with Comdirect OAuth2 and retrieve primary access/refresh tokens.
        Returns a dict containing primary tokens and expiration info.
        See chapter 2.1 of comdirect REST API documentation for details.

        Private method - use `await ComdirectClient.create()` for normal usage.
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": username,
            "password": password,
            "grant_type": "password",
            "scope": scope,
        }
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(self.OAUTH_URL, headers=headers, data=data)

            # Log error response before raising exception
            if response.status_code != httpx.codes.OK:
                logger.error(
                    "Authentication failed. Status code: %s, response: %s",
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()
            data = response.json()

            # Parse response using AuthResponse model for validation
            auth_response = AuthResponse(**data)

            # Save token info
            self.primary_access_token = auth_response.access_token
            self.refresh_token = auth_response.refresh_token
            self.token_expires_at = auth_response.expires_at.timestamp()
            self.scope = auth_response.scope
            self.kdnr = auth_response.kdnr  # Kundennummer
            self.bpid = auth_response.bpid  # Interne Identifikationsnummer
            self.kontaktid = auth_response.kontakt_id  # Interne Identifikationsnummer
            return data

    async def _get_session_status(self) -> dict[str, Any]:
        """
        Retrieve session status
        See chapter 2.2 of comdirect REST API documentation for details.

        Private method - use `await ComdirectClient.create()` for normal usage.
        """
        url = f"{self.BASE_URL}/session/clients/user/v1/sessions"

        self.session_id = uuid.uuid4().hex  # 32 hex chars

        if self.primary_access_token is None:
            raise ValueError("No access token available. Please authenticate first.")

        headers = self._request_headers(self.primary_access_token)

        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(url, headers=headers)
            # Log error response before raising exception
            if response.status_code != httpx.codes.OK:
                logger.error(
                    "Session status error: %s, response: %s",
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()
            data = response.json()
            self.session_id = data[0].get("identifier")
            self.session_tan_active = data[0].get("sessionTanActive", False)
            self.activated_2fa = data[0].get("activated2FA", False)
            return data

    async def _create_validate_session_tan(self) -> dict[str, Any]:
        """
        Orchestrates the TAN activation workflow:
        1. Initiates the TAN challenge.
        2. Waits for TAN confirmation (push / app).
        3. Activates the session TAN.
        Returns the activation response as a dict.
        See chapter 2.3 of comdirect REST API documentation for details.

        Private method - use `await ComdirectClient.create()` for normal usage.
        """
        # Check prerequisites
        if not self.session_id:
            raise ValueError(
                "No session ID available. Please establish a session first."
            )
        if not self.primary_access_token:
            raise ValueError("No access token available. Please authenticate first.")

        # Step 1: Initiate TAN challenge
        logger.info("Initiating TAN challenge...")
        challenge_data = await self._initiate_tan_challenge()
        logger.debug("TAN challenge data: %s", challenge_data)
        challenge_id = challenge_data.get("id")
        tan_type = challenge_data.get("typ")
        auth_url = challenge_data.get("auth_url")
        available_tan_types = challenge_data.get("availableTypes", [])

        if not challenge_id:
            raise ValueError("No challenge ID received from TAN initiation")
        if not auth_url:
            raise ValueError("No authentication URL received from TAN initiation")

        logger.info(
            "TAN challenge initiated. Challenge ID: %s, Type: %s, Available types: %s. "
            "Please check your smartphone and approve the TAN request.",
            challenge_id,
            tan_type,
            available_tan_types,
        )

        # Step 2: Wait for TAN confirmation using the correct URL

        data = await self._wait_for_tan_confirmation(auth_url)
        if data.get("status") == "AUTHENTICATED":
            self.session_tan_active = True
            self.activated_2fa = True
            logger.info("TAN authentication successful, activating session TAN...")
        else:
            raise ValueError(f"Unexpected TAN status after confirmation: {data}")
        # Step 3: Activate session TAN
        data = await self._activate_session_tan(challenge_id)
        return data

    async def _activate_session_tan(self, challenge_id: str):
        """
        Activate session TAN
        See chapter 2.4 of comdirect REST API documentation for details.
        """
        logger.debug("Activating session TAN with challenge ID: %s", challenge_id)

        url = f"{self.BASE_URL}/session/clients/user/v1/sessions/{self.session_id}"

        if not self.session_id:
            raise ValueError("No session ID available. Please establish session first.")

        if self.primary_access_token is None:
            raise ValueError("No access token available. Please authenticate first.")

        headers = self._request_headers(
            self.primary_access_token,
            extra={"x-once-authentication-info": json.dumps({"id": challenge_id})},
        )
        payload = {
            "identifier": self.session_id,
            "sessionTanActive": True,
            "activated2FA": True,
        }
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.patch(url, headers=headers, json=payload)
            # Log error response before raising exception
            if response.status_code != httpx.codes.OK:
                logger.error(
                    "Error activating session TAN: %s, response: %s",
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()
            data = response.json()
            logger.debug("Session TAN activation response: %s", data)
            return data

    async def _initiate_tan_challenge(self) -> dict[str, Any]:
        """
        Start a TAN challenge for the client session.
        Stores challenge ID and link in self.challenge_id / self.challenge_link.
        Returns dict containing the challenge ID, type, and link.
        """

        url = f"{self.BASE_URL}/session/clients/user/v1/sessions/{self.session_id}/validate"

        if not self.session_id:
            raise ValueError(
                "No session ID available. Please establish a session first."
            )
        if not self.primary_access_token:
            raise ValueError("No access token available. Please authenticate first.")

        headers = self._request_headers(self.primary_access_token)

        payload = {
            "identifier": self.session_id,
            "sessionTanActive": True,
            "activated2FA": True,
        }
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(url, headers=headers, json=payload)

        # Log error response before raising exception
        if response.status_code != httpx.codes.CREATED:
            logger.error(
                "Error initiating TAN challenge: %s, response: %s",
                response.status_code,
                response.text,
            )
        response.raise_for_status()

        # Log response for debugging
        data = response.json()
        logger.debug("TAN initiation response: %s", data)

        # Extract authentication URL
        auth_header = response.headers.get("x-once-authentication-info")
        if not auth_header:
            raise ValueError("Missing 'x-once-authentication-info' header in response")

        try:
            data = json.loads(auth_header)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in 'x-once-authentication-info' header: {e}"
            ) from e

        logger.debug("Authentication info: %s", data)

        # Extract the correct authentication URL from the response
        auth_url = data.get("link", {}).get("href")
        if not auth_url:
            raise ValueError("Missing authentication URL in TAN challenge response")

        logger.debug("Authentication URL: %s", auth_url)

        # Add the auth_url to the data for later use
        data["auth_url"] = auth_url
        self.challenge_id = data.get("id")
        self.tan_type = data.get("typ")
        self.available_tan_types = data.get("availableTypes", [])
        self.challenge_link = auth_url
        return data

    async def _wait_for_tan_confirmation(
        self, auth_url: str, max_attempts: int = 30, delay: int = 2
    ) -> dict[str, Any]:
        """Wait for TAN confirmation by polling the authentication URL."""
        logger.info("Waiting for TAN confirmation...")
        logger.debug("TAN confirmation URL: %s", auth_url)

        full_url = f"https://api.comdirect.de{auth_url}"

        if self.primary_access_token is None:
            raise ValueError("No access token available. Please authenticate first.")

        headers = self._request_headers(self.primary_access_token)

        for attempt in range(max_attempts):
            try:
                # Poll the authentication status using the provided URL
                async with httpx.AsyncClient(follow_redirects=False) as client:
                    response = await client.get(full_url, headers=headers)

                    if response.status_code == httpx.codes.OK:
                        data = response.json()
                        status = data.get("status")

                        logger.debug(
                            "TAN status check (attempt %d/%d): %s",
                            attempt + 1,
                            max_attempts,
                            status,
                        )

                        match status:
                            case "AUTHENTICATED":
                                logger.info("TAN confirmed successfully!")
                                return data
                            case "PENDING" | "ACTIVE":
                                logger.debug(
                                    "TAN challenge still pending (status: %s), retrying...",
                                    status,
                                )
                                await asyncio.sleep(delay)
                                continue
                            case _:
                                # Unexpected status (e.g., FAILED, REJECTED) - fail immediately
                                raise ValueError(
                                    f"Unexpected TAN status: {status}. "
                                    f"Expected AUTHENTICATED, PENDING, or ACTIVE."
                                )
                    else:
                        logger.warning(
                            "Unexpected status code: %s, response: %s",
                            response.status_code,
                            response.text,
                        )
                        if response.status_code == httpx.codes.NOT_FOUND:
                            logger.error(
                                "Authentication challenge not found. It may have expired."
                            )
                            break
                        response.raise_for_status()

            except httpx.HTTPError as e:
                logger.warning("HTTP error checking TAN status (attempt %d): %s", attempt + 1, e)
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(delay)

        raise TimeoutError(
            f"TAN confirmation timed out after {max_attempts} attempts "
            f"({max_attempts * delay} seconds)"
        )

    # ==================== BANKING/BROKERAGE ACCESS ====================

    async def _get_banking_brokerage_access(self) -> dict[str, Any]:
        """
        Get an access token with BANKING/BROKERAGE permissions using the cd_secondary flow.
        See chapter 2.5 of comdirect REST API documentation for details.
        """
        if not self.primary_access_token:
            raise ValueError(
                "No base access token available. Please authenticate first."
            )
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "cd_secondary",
            # Must be the primary OAuth token from initial authentication
            "token": self.primary_access_token,
        }
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(self.OAUTH_URL, headers=headers, data=data)

            # Log error response before raising exception
            if response.status_code != httpx.codes.OK:
                logger.error(
                    "Error cd_secondary access flow: %s, response: %s",
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()
            data = response.json()

            # Parse response using AuthResponse model for validation
            auth_response = AuthResponse(**data)

            # Save banking token info
            self.banking_access_token = auth_response.access_token
            self.refresh_token = auth_response.refresh_token
            self.scope = auth_response.scope
            self.kdnr = auth_response.kdnr  # Kundennummer
            self.bpid = auth_response.bpid  # Interne Identifikationsnummer
            self.kontaktid = auth_response.kontakt_id  # Interne Identifikationsnummer
            return data

    # ==================== TOKEN MANAGEMENT ====================

    async def refresh_access_token(self) -> dict[str, Any]:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            raise ValueError("No refresh token available. Please authenticate first.")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with httpx.AsyncClient() as client:
            response = await client.post(self.OAUTH_URL, headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()

            # Parse response using AuthResponse model for validation
            auth_response = AuthResponse(**data)

            # Update tokens
            self.primary_access_token = auth_response.access_token
            self.refresh_token = auth_response.refresh_token
            self.token_expires_at = auth_response.expires_at.timestamp()
            self.scope = auth_response.scope
            self.kdnr = auth_response.kdnr  # Kundennummer
            self.bpid = auth_response.bpid  # Interne Identifikationsnummer
            self.kontaktid = auth_response.kontakt_id  # Interne Identifikationsnummer
            return data



    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        return time.time() >= self.token_expires_at

    # ==================== BANKING API ====================

    async def get_account_balances(self) -> AccountBalances:
        """Get the account balance."""

        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/banking/clients/user/v2/accounts/balances"

            headers = self._request_headers(self.banking_access_token)

            response = await client.get(
                url=url,
                headers=headers,
            )
            response.raise_for_status()
            account_balances = response.json()
            return AccountBalances(**account_balances)

    async def get_account_depots(self) -> AccountDepots:
        """Get the account depots."""

        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/brokerage/clients/user/v3/depots"
            headers = self._request_headers(self.banking_access_token)

            response = await client.get(
                url=url,
                headers=headers,
            )
            response.raise_for_status()
            depots = response.json()
            return AccountDepots(**depots)

    async def get_account_transactions(
        self,
        account_id: str,
        transaction_state: str = "BOTH",
        transaction_direction: str = "CREDIT_AND_DEBIT",
        paging_first: int = 0,
        with_attr: str | None = None,
    ) -> AccountTransactions:
        """
        Get transactions for a specific account.

        Args:
            account_id: Account identifier (UUID)
            transaction_state: BOOKED, NOTBOOKED, or BOTH (default)
            transaction_direction: CREDIT, DEBIT, or CREDIT_AND_DEBIT (default)
            paging_first: Index of the first transaction (default: 0)
            with_attr: Additional attributes to load (e.g., "account")

        Returns:
            AccountTransactions object with list of transactions
        """
        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/banking/v1/accounts/{account_id}/transactions"
            headers = self._request_headers(self.banking_access_token)

            params = {
                "transactionState": transaction_state,
                "transactionDirection": transaction_direction,
                "paging-first": paging_first,
            }
            if with_attr:
                params["with-attr"] = with_attr

            response = await client.get(url=url, headers=headers, params=params)
            response.raise_for_status()
            transactions = response.json()
            return AccountTransactions(**transactions)

    # ==================== BROKERAGE API ====================

    async def get_depot_positions(
        self,
        depot_id: str,
        instrument_id: str | None = None,
        with_attr: str | None = None,
        without_attr: list[str] | None = None,
    ) -> DepotPositions:
        """
        Get securities positions for a specific depot.

        Args:
            depot_id: Depot identifier (UUID)
            instrument_id: Optional filter by instrument (WKN, ISIN, or UUID)
            with_attr: Additional attributes to enable (e.g., "instrument")
            without_attr: Attributes to disable (e.g., ["depot", "positions"])

        Returns:
            DepotPositions object with list of positions
        """
        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/brokerage/v3/depots/{depot_id}/positions"
            headers = self._request_headers(self.banking_access_token)

            params = {}
            if instrument_id:
                params["instrumentId"] = instrument_id
            if with_attr:
                params["with-attr"] = with_attr
            if without_attr:
                params["without-attr"] = without_attr

            response = await client.get(url=url, headers=headers, params=params)
            response.raise_for_status()
            positions = response.json()
            return DepotPositions(**positions)

    async def get_depot_position(
        self, depot_id: str, position_id: str, with_attr: str | None = None
    ) -> DepotPosition:
        """
        Get a single position from a depot.

        Args:
            depot_id: Depot identifier (UUID)
            position_id: Position identifier (UUID)
            with_attr: Additional attributes to enable (e.g., "instrument")

        Returns:
            DepotPosition object
        """
        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = (
                f"{self.BASE_URL}/brokerage/v3/depots/{depot_id}"
                f"/positions/{position_id}"
            )
            headers = self._request_headers(self.banking_access_token)

            params = {}
            if with_attr:
                params["with-attr"] = with_attr

            response = await client.get(url=url, headers=headers, params=params)
            response.raise_for_status()
            position = response.json()
            return DepotPosition(**position)

    async def get_depot_transactions(
        self,
        depot_id: str,
        isin: str | None = None,
        wkn: str | None = None,
        instrument_id: str | None = None,
        min_booking_date: str = "-180d",
    ) -> DepotTransactions:
        """
        Get transactions for a specific depot.

        Args:
            depot_id: Depot identifier (UUID)
            isin: Optional filter by ISIN
            wkn: Optional filter by WKN
            instrument_id: Optional filter by instrument ID (UUID)
            min_booking_date: Earliest booking date (YYYY-MM-DD or offset like "-180d")

        Returns:
            DepotTransactions object with list of transactions
        """
        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/brokerage/v3/depots/{depot_id}/transactions"
            headers = self._request_headers(self.banking_access_token)

            params = {"min-bookingDate": min_booking_date}
            if isin:
                params["isin"] = isin
            if wkn:
                params["wkn"] = wkn
            if instrument_id:
                params["instrumentId"] = instrument_id

            response = await client.get(url=url, headers=headers, params=params)
            response.raise_for_status()
            transactions = response.json()
            return DepotTransactions(**transactions)

    async def get_instrument(
        self,
        instrument_id: str,
        with_attr: list[str] | None = None,
        without_attr: list[str] | None = None,
    ) -> Instruments:
        """
        Get information about an instrument.

        Args:
            instrument_id: Instrument identification (WKN, ISIN, or symbol)
            with_attr: Additional attributes to enable
                      (e.g., ["orderDimensions", "fundDistribution", "derivativeData"])
            without_attr: Attributes to disable (e.g., ["staticData"])

        Returns:
            Instruments object (note: API returns a list even for single instrument)
        """
        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/brokerage/v1/instruments/{instrument_id}"
            headers = self._request_headers(self.banking_access_token)

            params = {}
            if with_attr:
                params["with-attr"] = with_attr
            if without_attr:
                params["without-attr"] = without_attr

            response = await client.get(url=url, headers=headers, params=params)
            response.raise_for_status()
            instruments = response.json()
            return Instruments(**instruments)

    # ==================== MESSAGES ====================

    async def get_documents(
        self,
        paging_first: int = 0,
        paging_count: int = 20,
    ) -> Documents:
        """
        Get a list of documents for the customer.

        Documents include statements, trade confirmations, tax reports, and other
        communications from Comdirect.

        Args:
            paging_first: Index of the first result to return (default: 0)
            paging_count: Maximum number of results to return (default: 20, max: 1000)

        Returns:
            Documents object containing a list of Document objects with metadata

        Raises:
            ValueError: If no banking access token is available
        """
        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/messages/clients/user/v2/documents"
            headers = self._request_headers(self.banking_access_token)

            params = {
                "paging-first": paging_first,
                "paging-count": min(paging_count, 1000),  # API max is 1000
            }

            logger.debug(f"Fetching documents list with params: {params}")
            response = await client.get(url=url, headers=headers, params=params)
            response.raise_for_status()
            documents = response.json()
            logger.info(
                f"Retrieved {len(documents.get('values', []))} documents"
            )
            return Documents(**documents)

    async def get_document(
        self,
        document_id: str,
    ) -> bytes:
        """
        Download a document by its ID.

        The document is typically returned as a PDF or HTML file.

        Args:
            document_id: The unique ID (UUID) of the document

        Returns:
            Raw bytes of the document (typically PDF or HTML)

        Raises:
            ValueError: If no banking access token is available
        """
        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/messages/v2/documents/{document_id}"
            headers = self._request_headers(self.banking_access_token)

            logger.debug(f"Downloading document: {document_id}")
            response = await client.get(url=url, headers=headers)
            response.raise_for_status()
            logger.info(
                f"Downloaded document {document_id} "
                f"({len(response.content)} bytes, {response.headers.get('content-type')})"
            )
            return response.content

    async def get_predocument(
        self,
        document_id: str,
    ) -> bytes:
        """
        Download a predocument by its document ID.

        A predocument is a preview or preliminary version of a document.

        Args:
            document_id: The unique ID (UUID) of the document

        Returns:
            Raw bytes of the predocument (typically PDF or HTML)

        Raises:
            ValueError: If no banking access token is available
        """
        if not self.banking_access_token:
            raise ValueError(
                "No banking access token available. Please obtain banking access first."
            )

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/messages/v2/documents/{document_id}/predocument"
            headers = self._request_headers(self.banking_access_token)

            logger.debug(f"Downloading predocument for: {document_id}")
            response = await client.get(url=url, headers=headers)
            response.raise_for_status()
            logger.info(
                f"Downloaded predocument for {document_id} "
                f"({len(response.content)} bytes, {response.headers.get('content-type')})"
            )
            return response.content
