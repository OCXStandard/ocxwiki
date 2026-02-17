#  Copyright (c) 2023-2026. OCX Consortium https://3docx.org. See the LICENSE
"""Pytest configuration and fixtures for ocxwiki tests."""

import pytest
from dokuwiki import DokuWikiError
from ocxwiki import WIKI_URL, USER, PSWD
from ocxwiki.client import WikiClient


@pytest.fixture(scope="session")
def wiki_client():
    """
    Create and login to WikiClient once per test session.

    This fixture provides an authenticated WikiClient instance that can be
    reused across all tests. Credentials are loaded from the .env file via
    the ocxwiki package initialization.

    Returns:
        WikiClient: An authenticated wiki client instance.

    Raises:
        DokuWikiError: If login fails.
    """
    client = WikiClient(WIKI_URL, USER, PSWD)

    # Attempt login
    try:
        result = client.login(USER, PSWD)
        if not result:
            pytest.fail("Wiki login failed: login() returned False")
    except DokuWikiError as e:
        pytest.fail(f"Wiki login failed with error: {e}")

    yield client

    # Teardown: You can add logout or cleanup here if needed
    # client.logout()  # if such method exists
