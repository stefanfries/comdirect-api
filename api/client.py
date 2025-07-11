import json
import time
import uuid
from typing import Any, Dict

import httpx

from .utils import timestamp


class ComdirectClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        self.session_id = None

    async def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Initial authentication to get access and refresh tokens."""
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(
                "https://api.comdirect.de/oauth/token",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "username": username,
                    "password": password,
                    "grant_type": "password",
                },
            )
            # Debugging: Show the response status code and text in case of an error
            if response.status_code != 200:
                print(f"Error: {response.status_code}, response: {response.text}")
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            self.token_expires_at = time.time() + data["expires_in"]
            return data

    async def get_session_status(self) -> Dict[str, Any]:
        # GET /session/clients/user/v1/sessions
        async with httpx.AsyncClient(follow_redirects=False) as client:
            self.session_id = str(uuid.uuid4())
            response = await client.get(
                "https://api.comdirect.de/api/session/clients/user/v1/sessions",
                headers={
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
                },
            )
            # Debugging: Show the response status code and text in case of an error
            if response.status_code != 200:
                print(f"Error: {response.status_code}, response: {response.text}")
            response.raise_for_status()
            data = response.json()
            self.session_id = data[0]["identifier"]
            return data

    async def validate_session_tan(self) -> Dict[str, Any]:
        """Validate the TAN for the session."""
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(
                f"https://api.comdirect.de/api/session/clients/user/v1/sessions/{self.session_id}/validate",
                headers={
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
                },
                json={
                    "identifier": self.session_id,
                    "sessionTanActive": True,
                    "activated2FA": True,
                },
            )
            # Debugging: Show the response status code and text in case of an error
            if response.status_code != 200:
                print(f"Error: {response.status_code}, response: {response.text}")
            response.raise_for_status()
            print(response.json())
            data = json.loads(response.headers["x-once-authentication-info"])
            print(data)
            challenge_id = data["id"]
            tan_type = data["challenge"]
            print(f"challenge_id: {challenge_id}, tan_type: {tan_type}")

            return data

    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            raise ValueError("No refresh token available. Please authenticate first.")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.comdirect.de/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
            )
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
                "https://api.comdirect.de/api/v1/accounts",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            response.raise_for_status()
            return response.json()
