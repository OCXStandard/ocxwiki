#  Copyright (c) 2023-2026. OCX Consortium https://3docx.org. See the LICENSE
"""Unit tests for WikiManager connect functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dokuwiki import DokuWikiError

from ocxwiki import WIKI_URL, USER, PSWD, TEST_WIKI_URL, TEST_PSWD
from ocxwiki.wiki_manager import WikiManager
from ocxwiki.client import WikiClient


class TestWikiManagerConnect:
    """Test suite for WikiManager connect functionality."""

    def test_wiki_manager_initialization(self):
        """Test that WikiManager initializes correctly."""
        manager = WikiManager(WIKI_URL)

        assert manager is not None
        assert manager._client is not None
        assert isinstance(manager._client, WikiClient)
        assert manager._schema_url is None
        assert manager.transformer is None

    def test_wiki_manager_initialization_with_schema_url(self):
        """Test WikiManager initialization with a schema URL."""
        schema_url = "https://example.com/schema.xsd"
        manager = WikiManager(WIKI_URL, schema_url=schema_url)

        assert manager is not None
        assert manager._schema_url == schema_url

    def test_client_property(self):
        """Test that the client property returns the WikiClient."""
        manager = WikiManager(WIKI_URL)
        client = manager.client

        assert client is not None
        assert isinstance(client, WikiClient)
        assert client == manager._client

    @patch.object(WikiClient, 'connect')
    def test_connect_successful(self, mock_connect):
        """Test successful connection to wiki."""
        mock_connect.return_value = True

        manager = WikiManager(WIKI_URL)
        result = manager._client.connect(user=USER, password=PSWD)

        assert result is True
        mock_connect.assert_called_once_with(user=USER, password=PSWD)

    @patch.object(WikiClient, 'connect')
    def test_connect_failed(self, mock_connect):
        """Test failed connection to wiki."""
        mock_connect.return_value = False

        manager = WikiManager(WIKI_URL)
        result = manager._client.connect(user=USER, password=PSWD)

        assert result is False
        mock_connect.assert_called_once_with(user=USER, password=PSWD)

    @patch.object(WikiClient, 'connect')
    def test_connect_with_exception(self, mock_connect):
        """Test connection that raises an exception."""
        mock_connect.side_effect = DokuWikiError("Connection failed")

        manager = WikiManager(WIKI_URL)

        with pytest.raises(DokuWikiError, match="Connection failed"):
            manager._client.connect(user=USER, password=PSWD)

    @patch.object(WikiClient, 'connect')
    def test_connect_with_invalid_credentials(self, mock_connect):
        """Test connection with invalid credentials."""
        mock_connect.return_value = False

        manager = WikiManager(WIKI_URL)
        result = manager._client.connect(user="invalid_user", password="invalid_password")

        assert result is False

    @patch.object(WikiClient, 'connect')
    @patch.object(WikiClient, 'wiki_version')
    def test_connect_and_get_version(self, mock_version, mock_connect):
        """Test connecting and retrieving wiki version."""
        mock_connect.return_value = True
        mock_version.return_value = "2024-02-06a \"Kaos\""

        manager = WikiManager(WIKI_URL)
        connected = manager._client.connect(user=USER, password=PSWD)

        assert connected is True

        version = manager._client.wiki_version()
        assert version == "2024-02-06a \"Kaos\""
        mock_version.assert_called_once()

    @patch.object(WikiClient, 'connect')
    @patch.object(WikiClient, 'current_url')
    def test_connect_verify_url(self, mock_current_url, mock_connect):
        """Test that the correct URL is set after connection."""
        mock_connect.return_value = True
        mock_current_url.return_value = WIKI_URL

        manager = WikiManager(WIKI_URL)
        connected = manager._client.connect(user=USER, password=PSWD)

        assert connected is True

        url = manager._client.current_url()
        assert url == WIKI_URL

    @patch.object(WikiClient, 'connect')
    def test_connect_multiple_times(self, mock_connect):
        """Test multiple connection attempts."""
        mock_connect.return_value = True

        manager = WikiManager(WIKI_URL)

        # First connection
        result1 = manager._client.connect(user=USER, password=PSWD)
        assert result1 is True

        # Second connection (should also work)
        result2 = manager._client.connect(user=USER, password=PSWD)
        assert result2 is True

        assert mock_connect.call_count == 2

    @patch.object(WikiClient, 'connect')
    def test_connect_with_empty_credentials(self, mock_connect):
        """Test connection attempt with empty credentials."""
        mock_connect.return_value = False

        manager = WikiManager(WIKI_URL)
        result = manager._client.connect(user="", password="")

        assert result is False

    @patch.object(WikiClient, 'connect')
    @patch.object(WikiClient, 'xmlrpc_version')
    def test_connect_and_check_xmlrpc_version(self, mock_xmlrpc_version, mock_connect):
        """Test getting XMLRPC version after connection."""
        mock_connect.return_value = True
        mock_xmlrpc_version.return_value = 9

        manager = WikiManager(WIKI_URL)
        connected = manager._client.connect(user=USER, password=PSWD)

        assert connected is True

        xmlrpc_ver = manager._client.xmlrpc_version()
        assert xmlrpc_ver == 9

    def test_wiki_manager_client_not_none_on_init(self):
        """Test that client is properly initialized and not None."""
        manager = WikiManager(WIKI_URL)

        assert manager._client is not None
        assert hasattr(manager._client, 'connect')
        assert hasattr(manager._client, 'current_url')
        assert hasattr(manager._client, 'wiki_version')

    @patch.object(WikiClient, 'connect')
    def test_connect_context_manager_usage(self, mock_connect):
        """Test that WikiManager can be used in context where connection state matters."""
        mock_connect.return_value = True

        manager = WikiManager(WIKI_URL)

        # Simulate using manager after connection
        connected = manager._client.connect(user=USER, password=PSWD)
        assert connected is True

        # Now manager should be usable for operations
        assert manager.client is not None

    @pytest.mark.parametrize("wiki_url,expected_result", [
        (WIKI_URL, True),
        (TEST_WIKI_URL, True),
        ("https://invalid.url", False),
    ])
    @patch.object(WikiClient, 'connect')
    def test_connect_different_urls(self, mock_connect, wiki_url, expected_result):
        """Test connection to different wiki URLs."""
        mock_connect.return_value = expected_result

        manager = WikiManager(wiki_url)
        result = manager._client.connect(user=USER, password=PSWD)

        assert result == expected_result


class TestWikiManagerClientMethods:
    """Test suite for WikiManager client-related methods."""

    @patch.object(WikiClient, 'connect')
    @patch.object(WikiClient, 'list_pages')
    def test_list_pages_after_connect(self, mock_list_pages, mock_connect):
        """Test listing pages after successful connection."""
        mock_connect.return_value = True
        mock_list_pages.return_value = {
            'page1': (1234567890, 1234567890, ''),
            'page2': (1234567891, 1234567891, '')
        }

        manager = WikiManager(WIKI_URL)
        manager._client.connect(user=USER, password=PSWD)

        pages = manager._client.list_pages(namespace='ocx-if:draft-schema')

        assert pages is not None
        assert len(pages) == 2
        assert 'page1' in pages
        assert 'page2' in pages



class TestWikiManagerPublishState:
    """Test suite for WikiManager publish state management."""

    def test_initial_publish_state(self):
        """Test that initial publish state is DRAFT."""
        from ocxwiki.wiki_manager import PublishState

        manager = WikiManager(WIKI_URL)

        assert manager._state == PublishState.DRAFT

    def test_set_publish_state_public(self):
        """Test setting publish state to PUBLIC."""
        from ocxwiki.wiki_manager import PublishState

        manager = WikiManager(WIKI_URL)
        manager.set_publish_state(PublishState.PUBLIC)

        assert manager._state == PublishState.PUBLIC

    def test_set_publish_state_draft(self):
        """Test setting publish state to DRAFT."""
        from ocxwiki.wiki_manager import PublishState

        manager = WikiManager(WIKI_URL)
        manager.set_publish_state(PublishState.DRAFT)

        assert manager._state == PublishState.DRAFT

    def test_get_publish_state(self):
        """Test getting publish state."""
        from ocxwiki.wiki_manager import PublishState

        manager = WikiManager(WIKI_URL)

        state = manager.get_publish_state()
        assert state == PublishState.DRAFT

    def test_get_publish_namespace_draft(self):
        """Test getting publish namespace for DRAFT state."""
        from ocxwiki.wiki_manager import PublishState

        manager = WikiManager(WIKI_URL)
        manager.set_publish_state(PublishState.DRAFT)

        namespace = manager.get_publish_namespace()
        assert 'draft' in namespace.lower()

    def test_get_publish_namespace_public(self):
        """Test getting publish namespace for PUBLIC state."""
        from ocxwiki.wiki_manager import PublishState

        manager = WikiManager(WIKI_URL)
        manager.set_publish_state(PublishState.PUBLIC)

        namespace = manager.get_publish_namespace()
        assert 'public' in namespace.lower()
