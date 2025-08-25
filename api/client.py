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
    Instantiate `ComdirectClient` with your client credentials, then use its methods to authenticate,
    manage sessions, validate TANs, refresh tokens, and retrieve account balances.

"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict

import httpx

from .utils import timestamp


class ComdirectClient:
    """Class to interact with the Comdirect API."""

    BASE_URL = "https://api.comdirect.de/api"
    OAUTH_URL = "https://api.comdirect.de/oauth/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session_tan: bool = False,
        two_factor_auth: bool = False,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.token_expires_at: float = 0
        self.session_tan = session_tan
        self.two_factor_auth = two_factor_auth
        self.scope: str | None = None
        self.session_id: str | None = None

    async def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """
        Generate initial OAuth2 access token and refresh token.
        See chapter 2.1 of comdirect REST API documentation for details.
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": username,
            "password": password,
            "grant_type": "password",
        }
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(self.OAUTH_URL, headers=headers, data=payload)

            # Debugging: Show the response status code and text in case of an error
            if response.status_code != httpx.codes.OK:
                print(f"Error: {response.status_code}, response: {response.text}")
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.token_expires_at = time.time() + data.get("expires_in", 0)
            self.scope = data.get("scope")
            return data

    async def get_session_status(self) -> Dict[str, Any]:
        """
        Retrieve session status
        See chapter 2.2 of comdirect REST API documentation for details.
        """
        self.session_id = uuid.uuid4().hex  # 32 hex chars
        url = f"{self.BASE_URL}/session/clients/user/v1/sessions"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "x-http-request-info": json.dumps(
                {
                    "clientRequestId": {
                        "sessionId": self.session_id,
                        "requestId": timestamp(),
                    }
                }
            ),
        }
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(url, headers=headers)
            # Debugging: Show the response status code and text in case of an error
            if response.status_code != httpx.codes.OK:
                print(f"Error: {response.status_code}, response: {response.text}")
            response.raise_for_status()
            data = response.json()
            self.session_id = data[0].get("identifier")
            self.session_tan = data[0].get("sessionTanActive", False)
            self.two_factor_auth = data[0].get("activated2FA", False)
            return data

    async def create_validate_session_tan(self) -> Dict[str, Any]:
        """
        Create and validate session TAN.
        See chapter 2.3 of comdirect REST API documentation for details.
        """
        # Check prerequisites
        if not self.session_id:
            raise ValueError(
                "No session ID available. Please establish a session first."
            )
        if not self.access_token:
            raise ValueError("No access token available. Please authenticate first.")

        # Step 1: Initiate TAN challenge
        print("Initiating TAN challenge...")
        challenge_data = await self._initiate_tan_challenge()
        challenge_id = challenge_data.get("id")
        tan_type = challenge_data.get("challenge")
        auth_url = challenge_data.get("auth_url")

        if not challenge_id:
            raise ValueError("No challenge ID received from TAN initiation")
        if not auth_url:
            raise ValueError("No authentication URL received from TAN initiation")

        print(
            f"TAN challenge initiated. Challenge ID: {challenge_id}, Type: {tan_type}"
        )
        print("Please check your smartphone and approve the TAN request...")

        # Step 2: Wait for TAN confirmation using the correct URL

        data = await self._wait_for_tan_confirmation(auth_url)
        if data.get("status") == "AUTHENTICATED":
            self.session_tan = True
            self.two_factor_auth = True
        else:
            self.session_tan = False
            self.two_factor_auth = False
        return data

    async def activate_session_tan(self):
        """
        Activate session TAN
        See chapter 2.4 of comdirect REST API documentation for details.
        """

    async def _initiate_tan_challenge(self) -> Dict[str, Any]:
        """Initiate the TAN challenge (sends push notification)."""

        url = f"{self.BASE_URL}/session/clients/user/v1/sessions/{self.session_id}/validate"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "x-http-request-info": json.dumps(
                {
                    "clientRequestId": {
                        "sessionId": self.session_id,
                        "requestId": timestamp(),
                    }
                }
            ),
        }
        payload = {
            "identifier": self.session_id,
            "sessionTanActive": True,  # replace by self.session_tan later
            "activated2FA": True,  # replace by self.two_factor_auth later
        }
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(url, headers=headers, json=payload)

        # Debugging: Show the response status code and text in case of an error
        if response.status_code != httpx.codes.CREATED:
            print(f"Error: {response.status_code}, response: {response.text}")
        response.raise_for_status()

        # Print response for debugging
        response_data = response.json()
        print(f"Response JSON: {response_data}")

        # Safely extract authentication info from headers
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
        return data

    async def _wait_for_tan_confirmation(
        self, auth_url: str, max_attempts: int = 15, delay: int = 2
    ) -> Dict[str, Any]:
        """Wait for TAN confirmation by polling the authentication URL."""
        print(f"Waiting for TAN confirmation using URL: {auth_url}")

        # Construct the full URL (auth_url is relative)
        full_url = f"https://api.comdirect.de{auth_url}"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "x-http-request-info": json.dumps(
                {
                    "clientRequestId": {
                        "sessionId": self.session_id,
                        "requestId": timestamp(),
                    }
                }
            ),
        }

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
                            f"Unexpected status code: {response.status_code}, response: {response.text}"
                        )
                        if response.status_code == 404:
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
            f"TAN confirmation timed out after {max_attempts} attempts ({max_attempts * delay} seconds)"
        )

    async def refresh_access_token(self) -> Dict[str, Any]:
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
            return data

    def _update_tokens(self, data: Dict[str, Any]):
        """Update the access token, refresh token, and expiration time."""
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 0)
        self.token_expires_at = (
            time.time() + expires_in - 30
        )  # Refresh 30 seconds before expiry

    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        return time.time() >= self.token_expires_at

    async def get_account_balance(self) -> Dict[str, Any]:
        """Get the account balance."""
        if self.is_token_expired():
            await self.refresh_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/v1/accounts",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            response.raise_for_status()
            return response.json()
