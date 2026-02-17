#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""Tests for WikiClient functionality."""


def test_is_connected(wiki_client):
    assert wiki_client.is_connected()

def test_url(wiki_client):
    assert wiki_client.current_url() == 'https://ocxwiki.3docx.org/'

def test_wiki_version(wiki_client):
    assert wiki_client._wiki.version == 'Release 2025-05-14b "Librarian"'

def test_xmlrpc_version(wiki_client):
    assert wiki_client._wiki.xmlrpc_version == 14


def test_list_pages(wiki_client):
    result = wiki_client.list_pages(namespace='public:schema:3.1.0:ocx')
    assert len(result) == 322



def test_get_data(wiki_client):
    result = wiki_client.get_data('public:schema:3.1.0:ocx:airpipeheight', False)
    assert result.get('OCX Version', None) == '3.1.0'



