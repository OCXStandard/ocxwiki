#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""Tests for WikiManager async methods."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from ocxwiki.wiki_manager import WikiManager, PublishState
from ocxwiki.client import WikiClient
from ocxwiki.error import OcxWikiError
from ocx_schema_parser.data_classes import OcxEnumerator, SchemaAttribute
from ocx_schema_parser.elements import OcxGlobalElement

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def wiki_manager():
    """Create a WikiManager instance for testing."""
    manager = WikiManager(wiki_url="http://test.wiki")
    return manager


@pytest.fixture
def mock_client():
    """Create a mock WikiClient."""
    client = Mock(spec=WikiClient)
    client.connect_async = AsyncMock(return_value=True)
    client.set_page_async = AsyncMock(return_value=True)
    client.append_page_async = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_transformer():
    """Create a mock Transformer."""
    transformer = Mock()
    transformer.parser = Mock()
    transformer.parser.get_schema_version.return_value = "3.0.0"
    transformer.parser.get_schema_namespace.return_value = "http://test.namespace"
    transformer.parser.get_namespaces.return_value = {}
    transformer.parser.get_xs_types.return_value = {}
    transformer.parser.get_schema_element_types.return_value = []
    transformer.parser.get_schema_attribute_types.return_value = []
    transformer.parser.get_schema_attribute_group_types.return_value = []
    transformer.parser.get_schema_simple_types.return_value = []
    transformer.get_enumerators.return_value = {}
    transformer.get_ocx_elements.return_value = []
    transformer.get_global_attributes.return_value = []
    transformer.get_simple_types.return_value = []
    return transformer


class TestWikiClientAsync:
    """Test WikiClient async methods."""

    @pytest.mark.asyncio
    async def test_connect_async(self):
        """Test async connect method."""
        client = WikiClient(url="http://test.wiki")

        with patch.object(client, 'connect', return_value=True) as mock_connect:
            result = await client.connect_async(user="testuser", password="testpass")

            assert result is True
            mock_connect.assert_called_once_with(user="testuser", password="testpass")

    @pytest.mark.asyncio
    async def test_set_page_async(self):
        """Test async set_page method."""
        client = WikiClient(url="http://test.wiki")

        with patch.object(client, 'set_page', return_value=True) as mock_set:
            result = await client.set_page_async(
                page="test_page",
                content="test content",
                summary="test summary",
                namespace="test_ns"
            )

            assert result is True
            mock_set.assert_called_once_with(
                page="test_page",
                content="test content",
                summary="test summary",
                namespace="test_ns",
                minor=False
            )

    @pytest.mark.asyncio
    async def test_append_page_async(self):
        """Test async append_page method."""
        client = WikiClient(url="http://test.wiki")

        with patch.object(client, 'append_page', return_value=True) as mock_append:
            result = await client.append_page_async(
                page="test_page",
                content="test content",
                summary="test summary"
            )

            assert result is True
            mock_append.assert_called_once()


class TestWikiManagerAsync:
    """Test WikiManager async methods."""

    @pytest.mark.asyncio
    async def test_connect_async_success(self, wiki_manager, mock_client):
        """Test successful async connection."""
        wiki_manager._client = mock_client

        result = await wiki_manager.connect_async(user="testuser", pswd="testpass")

        assert result is True
        assert wiki_manager._wiki_user == "testuser"
        mock_client.connect_async.assert_called_once_with(user="testuser", password="testpass")

    @pytest.mark.asyncio
    async def test_connect_async_failure(self, wiki_manager, mock_client):
        """Test failed async connection."""
        mock_client.connect_async.return_value = False
        wiki_manager._client = mock_client

        result = await wiki_manager.connect_async(user="testuser", pswd="testpass")

        assert result is False
        assert wiki_manager._wiki_user != "testuser"

    @pytest.mark.asyncio
    async def test_publish_page_async_without_transformer(self, wiki_manager):
        """Test publish_page_async raises error without transformer."""
        mock_page = Mock(spec=OcxGlobalElement)

        with pytest.raises(OcxWikiError, match="No schema url has been processed"):
            await wiki_manager.publish_page_async(mock_page)

    @pytest.mark.asyncio
    async def test_publish_page_async_success(self, wiki_manager, mock_client, mock_transformer):
        """Test successful async page publishing."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Setup mock page
        mock_page = Mock(spec=OcxGlobalElement)
        mock_page.get_prefix.return_value = "ocx"
        mock_page.get_name.return_value = "TestElement"
        mock_page.get_tag.return_value = "{http://test.namespace}TestElement"

        # Initialize wiki schema
        with patch('ocxwiki.wiki_manager.Render.page') as mock_render:
            mock_render.return_value = "test content"
            with patch.object(wiki_manager, 'transform'):
                wiki_manager.process_schema_folder(Path('.'))

            result = await wiki_manager.publish_page_async(mock_page)

            assert result is True
            mock_client.set_page_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_enum_async_success(self, wiki_manager, mock_client, mock_transformer):
        """Test successful async enum publishing."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Setup mock enum
        mock_enum = Mock(spec=OcxEnumerator)
        mock_enum.prefix = "ocx"
        mock_enum.name = "MaterialType"

        with patch('ocxwiki.wiki_manager.Render.enum') as mock_render:
            mock_render.return_value = "test enum content"
            with patch.object(wiki_manager, 'transform'):
                wiki_manager.process_schema_folder(Path('.'))

            result = await wiki_manager.publish_enum_async(mock_enum)

            assert result is True
            mock_client.set_page_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_attribute_async_success(self, wiki_manager, mock_client, mock_transformer):
        """Test successful async attribute publishing."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Setup mock attribute
        mock_attr = Mock(spec=SchemaAttribute)
        mock_attr.prefix = "ocx"
        mock_attr.name = "TestAttribute"

        with patch('ocxwiki.wiki_manager.Render.attribute') as mock_render:
            mock_render.return_value = "test attribute content"
            with patch.object(wiki_manager, 'transform'):
                wiki_manager.process_schema_folder(Path('.'))

            result = await wiki_manager.publish_attribute_async(mock_attr)

            assert result is True
            mock_client.set_page_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_simple_type_async_success(self, wiki_manager, mock_client, mock_transformer):
        """Test successful async simple type publishing."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Setup mock simple type
        mock_simple = Mock(spec=SchemaAttribute)
        mock_simple.prefix = "ocx"
        mock_simple.name = "TestSimpleType"

        with patch('ocxwiki.wiki_manager.Render.attribute') as mock_render:
            mock_render.return_value = "test simple type content"
            with patch.object(wiki_manager, 'transform'):
                wiki_manager.process_schema_folder(Path('.'))

            result = await wiki_manager.publish_simple_type_async(mock_simple)

            assert result is True
            mock_client.set_page_async.assert_called_once()


class TestBatchPublishingAsync:
    """Test batch async publishing methods."""

    @pytest.mark.asyncio
    async def test_publish_all_pages_async(self, wiki_manager, mock_client, mock_transformer):
        """Test batch publishing of pages."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Create mock pages
        mock_pages = []
        for i in range(5):
            page = Mock(spec=OcxGlobalElement)
            page.get_prefix.return_value = "ocx"
            page.get_name.return_value = f"Element{i}"
            page.get_tag.return_value = f"{{http://test.namespace}}Element{i}"
            mock_pages.append(page)

        with patch('ocxwiki.wiki_manager.Render.page') as mock_render:
            mock_render.return_value = "test content"
            with patch.object(wiki_manager, 'transform'):
                wiki_manager.process_schema_folder(Path('.'))

            results = await wiki_manager.publish_all_pages_async(mock_pages, max_concurrent=2)

            assert len(results) == 5
            assert all(r is True for r in results)
            assert mock_client.set_page_async.call_count == 5

    @pytest.mark.asyncio
    async def test_publish_all_enums_async(self, wiki_manager, mock_client, mock_transformer):
        """Test batch publishing of enums."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Create mock enums
        mock_enums = {}
        for i in range(3):
            enum = Mock(spec=OcxEnumerator)
            enum.prefix = "ocx"
            enum.name = f"Enum{i}"
            mock_enums[f"Enum{i}"] = enum

        with patch('ocxwiki.wiki_manager.Render.enum') as mock_render:
            mock_render.return_value = "test enum content"
            with patch.object(wiki_manager, 'transform'):
                wiki_manager.process_schema_folder(Path('.'))

            results = await wiki_manager.publish_all_enums_async(mock_enums, max_concurrent=2)

            assert len(results) == 3
            assert all(r is True for r in results)

    @pytest.mark.asyncio
    async def test_publish_all_attributes_async(self, wiki_manager, mock_client, mock_transformer):
        """Test batch publishing of attributes."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Create mock attributes
        mock_attrs = []
        for i in range(4):
            attr = Mock(spec=SchemaAttribute)
            attr.prefix = "ocx"
            attr.name = f"Attr{i}"
            mock_attrs.append(attr)

        with patch('ocxwiki.wiki_manager.Render.attribute') as mock_render:
            mock_render.return_value = "test attribute content"
            with patch.object(wiki_manager, 'transform'):
                wiki_manager.process_schema_folder(Path('.'))

            results = await wiki_manager.publish_all_attributes_async(mock_attrs, max_concurrent=2)

            assert len(results) == 4
            assert all(r is True for r in results)

    @pytest.mark.asyncio
    async def test_publish_complete_schema_async_without_transformer(self, wiki_manager):
        """Test publish_complete_schema_async raises error without transformer."""
        with pytest.raises(OcxWikiError, match="No schema url has been processed"):
            await wiki_manager.publish_complete_schema_async()

    @pytest.mark.asyncio
    async def test_publish_complete_schema_async_success(self, wiki_manager, mock_client, mock_transformer):
        """Test successful complete schema publishing."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Setup mock data
        mock_pages = [Mock(spec=OcxGlobalElement) for _ in range(2)]
        for i, page in enumerate(mock_pages):
            page.get_prefix.return_value = "ocx"
            page.get_name.return_value = f"Element{i}"
            page.get_tag.return_value = f"{{http://test.namespace}}Element{i}"

        mock_enums = {f"Enum{i}": Mock(spec=OcxEnumerator) for i in range(2)}
        for i, (name, enum) in enumerate(mock_enums.items()):
            enum.prefix = "ocx"
            enum.name = name

        mock_attrs = [Mock(spec=SchemaAttribute) for _ in range(2)]
        for i, attr in enumerate(mock_attrs):
            attr.prefix = "ocx"
            attr.name = f"Attr{i}"

        mock_simple = [Mock(spec=SchemaAttribute) for _ in range(2)]
        for i, simple in enumerate(mock_simple):
            simple.prefix = "ocx"
            simple.name = f"Simple{i}"

        mock_transformer.get_ocx_elements.return_value = mock_pages
        mock_transformer.get_enumerators.return_value = mock_enums
        mock_transformer.get_global_attributes.return_value = mock_attrs
        mock_transformer.get_simple_types.return_value = mock_simple

        with patch('ocxwiki.wiki_manager.Render.page') as mock_page_render:
            mock_page_render.return_value = "page content"
            with patch('ocxwiki.wiki_manager.Render.enum') as mock_enum_render:
                mock_enum_render.return_value = "enum content"
                with patch('ocxwiki.wiki_manager.Render.attribute') as mock_attr_render:
                    mock_attr_render.return_value = "attribute content"
                    with patch.object(wiki_manager, 'transform'):
                        wiki_manager.process_schema_folder(Path('.'))

                    results = await wiki_manager.publish_complete_schema_async(max_concurrent=3)

                    assert results['pages'] == 2
                    assert results['enums'] == 2
                    assert results['attributes'] == 2
                    assert results['simple_types'] == 2
                    assert len(results['errors']) == 0

    @pytest.mark.asyncio
    async def test_publish_with_errors(self, wiki_manager, mock_client, mock_transformer):
        """Test batch publishing with some errors."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Make some calls fail
        call_count = [0]

        async def mock_set_page_async(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                raise Exception("Test error")
            return True

        mock_client.set_page_async.side_effect = mock_set_page_async

        # Create mock pages
        mock_pages = []
        for i in range(4):
            page = Mock(spec=OcxGlobalElement)
            page.get_prefix.return_value = "ocx"
            page.get_name.return_value = f"Element{i}"
            page.get_tag.return_value = f"{{http://test.namespace}}Element{i}"
            mock_pages.append(page)

        with patch('ocxwiki.wiki_manager.Render.page') as mock_render:
            mock_render.return_value = "test content"
            with patch.object(wiki_manager, 'transform'):
                wiki_manager.process_schema_folder(Path('.'))

            results = await wiki_manager.publish_all_pages_async(mock_pages, max_concurrent=2)

            # Should have 2 successes and 2 exceptions
            successes = sum(1 for r in results if r is True)
            errors = sum(1 for r in results if isinstance(r, Exception))

            assert successes == 2
            assert errors == 2


class TestAsyncHelper:
    """Test async helper utilities."""

    def test_run_async(self):
        """Test run_async function."""
        from ocxwiki.async_helper import run_async

        async def sample_coro():
            await asyncio.sleep(0.01)
            return "test result"

        result = run_async(sample_coro())
        assert result == "test result"

    def test_async_command_decorator(self):
        """Test async_command decorator."""
        from ocxwiki.async_helper import async_command

        @async_command
        async def sample_async_func(value: int):
            await asyncio.sleep(0.01)
            return value * 2

        # Should be callable as sync function
        result = sample_async_func(5)
        assert result == 10


class TestConcurrencyControl:
    """Test concurrency control with semaphores."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, wiki_manager, mock_client, mock_transformer):
        """Test that semaphore properly limits concurrent operations."""
        wiki_manager._client = mock_client
        wiki_manager._transformer = mock_transformer

        # Track concurrent calls
        concurrent_calls = []
        max_concurrent_seen = [0]

        async def track_concurrent_call(*args, **kwargs):
            concurrent_calls.append(1)
            current = len(concurrent_calls)
            if current > max_concurrent_seen[0]:
                max_concurrent_seen[0] = current

            await asyncio.sleep(0.05)  # Simulate work
            concurrent_calls.pop()
            return True

        mock_client.set_page_async.side_effect = track_concurrent_call

        # Create many mock pages
        mock_pages = []
        for i in range(10):
            page = Mock(spec=OcxGlobalElement)
            page.get_prefix.return_value = "ocx"
            page.get_name.return_value = f"Element{i}"
            page.get_tag.return_value = f"{{http://test.namespace}}Element{i}"
            mock_pages.append(page)

        with patch('ocxwiki.wiki_manager.Render.page') as mock_render:
            mock_render.return_value = "test content"
            with patch.object(wiki_manager, 'transform'):
                wiki_manager.process_schema_folder(Path('.'))

            # Limit to 3 concurrent operations
            await wiki_manager.publish_all_pages_async(mock_pages, max_concurrent=3)

            # Should never exceed the limit
            assert max_concurrent_seen[0] <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
