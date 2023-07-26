#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE

from dokuwiki import DokuWikiError
from ocxwiki import WIKI_URL, USER, PSWD
from ocxwiki.client import WikiClient

# Global wiki client
client = WikiClient(WIKI_URL, USER, PSWD)


def test_media_info():
    assert False


def test_login():
    try:
        result = client.login(USER, PSWD)
    except DokuWikiError as e:
        print(f'Wiki error: {e}')
        assert False
    assert result is True


def test_list_pages():
    result = client.list_pages('ocx')
    assert len(result) == 327


def test_changes():
    assert False


def test_append_page():
    assert False


def test_set_page():
    assert False


def test_get_data():
    result = client.get_data('ocx:airpipeheight', False)
    print(result)
    assert True


def test_list_media():
    result = client.list_media('wiki')
    print(result)
    assert False


def test_media_changes():
    assert False


def test_add_media():
    assert False


def test_media_delete():
    assert False
