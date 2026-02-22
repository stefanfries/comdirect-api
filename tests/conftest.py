"""
conftest.py
This module contains pytest fixtures for testing the Comdirect API client.
It provides reusable fixtures for test client credentials and for creating
an instance of the ComdirectClient with those credentials.

"""

import pytest

from comdirect_api.client import ComdirectClient


# pylint: disable=redefined-outer-name
@pytest.fixture
def creds():
    """Fixture providing test client credentials."""
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "username": "test_username",
        "password": "test_password",
    }


@pytest.fixture
def client_instance(creds):
    """Fixture providing a ComdirectClient instance."""
    return ComdirectClient(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
    )
