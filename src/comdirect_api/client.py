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
import time
import uuid
from typing import Any

import httpx

from .models.accounts import AccountBalances
from .models.depots import AccountDepots, DepotPosition, DepotPositions
from .models.instruments import Instruments
from .models.transactions import AccountTransactions, DepotTransactions
from .utils import timestamp


class ComdirectClient:
    """Class to interact with the Comdirect API."""

    BASE_URL = "https://api.comdirect.de/api"
    OAUTH_URL = "https://api.comdirect.de/oauth/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
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

    async def authenticate(
        self, username: str, password: str, scope: str = "SESSION_RW"
    ) -> dict[str, Any]:
        """
        Authenticate with Comdirect OAuth2 and retrieve primary access/refresh tokens.
        Returns a dict containing primary tokens and expiration info.
        See chapter 2.1 of comdirect REST API documentation for details.
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

            # Debugging: Show the response status code and text in case of an error
            if response.status_code != httpx.codes.OK:
                print(
                    f"Authentication failed. Status code: {response.status_code}, "
                    f"response: {response.text}"
                )
            response.raise_for_status()
            data = response.json()

            # save token info
            self.primary_access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.token_expires_at = (
                time.time() + data.get("expires_in", 0) - 30
            )  # Refresh 30 seconds before expiry
            self.scope = data.get("scope")
            self.kdnr = data.get("kdnr")  # Kundennummer
            self.bpid = data.get("bpid")  # Interne Identifikationsnummer
            self.kontaktid = data.get("kontaktId")  # Interne Identifikationsnummer
            return data

    async def get_session_status(self) -> dict[str, Any]:
        """
        Retrieve session status
        See chapter 2.2 of comdirect REST API documentation for details.
        """
        url = f"{self.BASE_URL}/session/clients/user/v1/sessions"

        self.session_id = uuid.uuid4().hex  # 32 hex chars

        if self.primary_access_token is None:
            raise ValueError("No access token available. Please authenticate first.")

        headers = self._request_headers(self.primary_access_token)

        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(url, headers=headers)
            # Debugging: Show the response status code and text in case of an error
            if response.status_code != httpx.codes.OK:
                print(f"Error: {response.status_code}, response: {response.text}")
            response.raise_for_status()
            data = response.json()
            self.session_id = data[0].get("identifier")
            self.session_tan_active = data[0].get("sessionTanActive", False)
            self.activated_2fa = data[0].get("activated2FA", False)
            return data

    async def create_validate_session_tan(self) -> dict[str, Any]:
        """
        Orchestrates the TAN activation workflow:
        1. Initiates the TAN challenge.
        2. Waits for TAN confirmation (push / app).
        3. Activates the session TAN.
        Returns the activation response as a dict.
        See chapter 2.3 of comdirect REST API documentation for details.
        """
        # Check prerequisites
        if not self.session_id:
            raise ValueError(
                "No session ID available. Please establish a session first."
            )
        if not self.primary_access_token:
            raise ValueError("No access token available. Please authenticate first.")

        # Step 1: Initiate TAN challenge
        print("Initiating TAN challenge...")
        challenge_data = await self._initiate_tan_challenge()
        print(f"TAN challenge data: {challenge_data}")
        challenge_id = challenge_data.get("id")
        tan_type = challenge_data.get("typ")
        auth_url = challenge_data.get("auth_url")
        available_tan_types = challenge_data.get("availableTypes", [])

        if not challenge_id:
            raise ValueError("No challenge ID received from TAN initiation")
        if not auth_url:
            raise ValueError("No authentication URL received from TAN initiation")

        print(
            f"Available TAN types: {available_tan_types}\n"
            f"TAN challenge initiated. Challenge ID: {challenge_id}, Type: {tan_type}\n"
            f"Please check your smartphone and approve the TAN request...\n"
        )

        # Step 2: Wait for TAN confirmation using the correct URL

        data = await self._wait_for_tan_confirmation(auth_url)
        if data.get("status") == "AUTHENTICATED":
            self.session_tan_active = True
            self.activated_2fa = True
            print("TAN authentication successful, activating session TAN...")
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
        print(f"Activating session TAN with challenge ID: {challenge_id}")

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
            # Debugging: Show the response status code and text in case of an error
            if response.status_code != httpx.codes.OK:
                # Debug output for troubleshooting
                print(
                    f"Error activating session TAN: {response.status_code}, {response.text}"
                )
            response.raise_for_status()
            data = response.json()
            print(f"Session TAN activation response: {data}")
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

        # Debugging: Show the response status code and text in case of an error
        if response.status_code != httpx.codes.CREATED:
            print(
                f"Error initiating TAN challenge: {response.status_code}, response: {response.text}"
            )
        response.raise_for_status()

        # Print response for debugging
        data = response.json()
        print(f"Response JSON: {data}")

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

        print(f"Authentication info: {data}")

        # Extract the correct authentication URL from the response
        auth_url = data.get("link", {}).get("href")
        if not auth_url:
            raise ValueError("Missing authentication URL in TAN challenge response")

        print(f"Authentication URL: {auth_url}")

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
        print(f"Waiting for TAN confirmation using URL: {auth_url}")

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

                        print(f"TAN status check (attempt {attempt + 1}): {status}")

                        match status:
                            case "AUTHENTICATED":
                                print("TAN confirmed successfully!")
                                return data
                            case "PENDING" | "ACTIVE":
                                print(
                                    f"TAN challenge still pending (status: {status})..."
                                )
                                await asyncio.sleep(delay)
                                continue
                            case _:
                                print(f"Unexpected TAN status: {status}")
                                # Continue polling for other statuses
                                await asyncio.sleep(delay)
                                continue
                    else:
                        print(
                            f"Unexpected status code: {response.status_code}, "
                            f"response: {response.text}"
                        )
                        if response.status_code == httpx.codes.NOT_FOUND:
                            print(
                                "Authentication challenge not found. It may have expired."
                            )
                            break
                        response.raise_for_status()

            except httpx.HTTPError as e:
                print(f"HTTP error checking TAN status (attempt {attempt + 1}): {e}")
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(delay)

        raise TimeoutError(
            f"TAN confirmation timed out after {max_attempts} attempts "
            f"({max_attempts * delay} seconds)"
        )

    async def get_banking_brokerage_access(self) -> dict[str, Any]:
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

            # Debugging: Show the response status code and text in case of an error
            if response.status_code != httpx.codes.OK:
                # Debug output for troubleshooting
                print(
                    f"Error cd_secondary access flow: {response.status_code}, {response.text}"
                )
            response.raise_for_status()
            data = response.json()
            self.banking_access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.scope = data.get("scope")
            self.kdnr = data.get("kdnr")  # Kundennummer
            self.bpid = data.get("bpid")  # Interne Identifikationsnummer
            self.kontaktid = data.get("kontaktId")  # Interne Identifikationsnummer
            return data

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
            self._update_tokens(data)
            self.scope = data.get("scope")
            self.kdnr = data.get("kdnr")  # Kundennummer
            self.bpid = data.get("bpid")  # Interne Identifikationsnummer
            self.kontaktid = data.get("kontaktId")  # Interne Identifikationsnummer
            return data

    def _update_tokens(self, data: dict[str, Any]):
        """Update the access token, refresh token, and expiration time."""
        self.primary_access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 0)
        self.token_expires_at = (
            time.time() + expires_in - 30
        )  # Refresh 30 seconds before expiry

    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        return time.time() >= self.token_expires_at

    async def get_account_balances(self) -> AccountBalances:
        """Get the account balance."""

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/banking/clients/user/v2/accounts/balances"

            if not self.banking_access_token:
                raise ValueError(
                    "No banking access token available. Please obtain banking access first."
                )
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

        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/brokerage/clients/user/v3/depots"
            if not self.banking_access_token:
                raise ValueError(
                    "No banking access token available. Please obtain banking access first."
                )
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
        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/banking/v1/accounts/{account_id}/transactions"
            if not self.banking_access_token:
                raise ValueError(
                    "No banking access token available. Please obtain banking access first."
                )
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
        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/brokerage/v3/depots/{depot_id}/positions"
            if not self.banking_access_token:
                raise ValueError(
                    "No banking access token available. Please obtain banking access first."
                )
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
        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = (
                f"{self.BASE_URL}/brokerage/v3/depots/{depot_id}"
                f"/positions/{position_id}"
            )
            if not self.banking_access_token:
                raise ValueError(
                    "No banking access token available. Please obtain banking access first."
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
        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/brokerage/v3/depots/{depot_id}/transactions"
            if not self.banking_access_token:
                raise ValueError(
                    "No banking access token available. Please obtain banking access first."
                )
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
        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}/brokerage/v1/instruments/{instrument_id}"
            if not self.banking_access_token:
                raise ValueError(
                    "No banking access token available. Please obtain banking access first."
                )
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
