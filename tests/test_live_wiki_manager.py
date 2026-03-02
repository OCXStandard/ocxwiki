#  Copyright (c) 2023-2026. OCX Consortium https://3docx.org. See the LICENSE
"""Tests for WikiManager functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from pathlib import Path

from ocxwiki import WIKI_URL, USER, PSWD, WORKING_DRAFT
from ocxwiki.wiki_manager import WikiManager, PublishState
from ocxwiki.client import WikiClient
from ocxwiki.error import OcxWikiError
from ocx_schema_parser.transformer import Transformer
from ocx_schema_parser.elements import OcxGlobalElement
from ocx_schema_parser.data_classes import OcxEnumerator, SchemaAttribute


@pytest.fixture
def wiki_manager():
    """Create a WikiManager instance for testing."""
    wiki_manger = WikiManager(
        wiki_url=WIKI_URL,
        schema_url=WORKING_DRAFT
    )
    assert wiki_manger.connect(user=USER, pswd=PSWD) is True
    return wiki_manger


class TestWikiManagerPageInfo:
    """Tests for WikiManager page information retrieval."""

    def test_get_page_info_success(self, wiki_manager):
        """Test successful retrieval of page information."""
        wiki_client = wiki_manager.client
        page_info = wiki_client.get_page_info('public:schema:3.1.0:ocx:airpipeheight')
        assert page_info is not None
        assert 'version' in page_info
        assert 'lastModified' in page_info

    def test_get_page_info_not_found(self, wiki_manager):
        """Test retrieval of non-existent page information."""
        client = wiki_manager.client
        page_info = client.get_page_info('public:schema:3.1.0:ocx:nonexistentpage')
        assert len(page_info) == 0


    def test_list_pages(self, wiki_manager):
        """Test retrieval of non-existent page information."""
        client = wiki_manager.client
        page_info = client.list_pages('public:schema:3.1.0:ocx')
        assert (len(page_info) == 322)  # For OCX version 3.1.0 there are 322 pages in this namespace

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
