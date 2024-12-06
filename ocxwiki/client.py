#  Copyright (c) 2023. #  OCX Consortium https://3docx.org. See the LICENSE
"""Python xml-rpc client for the OCX wiki."""

# System imports
from typing import Dict, OrderedDict, Optional
import datetime
import requests.exceptions as http_error
from pathlib import Path
# Third party imports
from dokuwiki import DokuWiki, DokuWikiError
from loguru import logger
# Module imports
from ocxwiki import USER, PSWD, WIKI_URL, DEFAULT_NSP
import ocxwiki.struct_data as struct_data


class WikiClient:
    """The WikiClient provides functionality for interacting with the OCX wiki pages.

    Args:
        url: the OCX wiki URL
        user: The wiki user
        password: The user password

    Attributes:
        _url: the wiki url
        _wiki: the DocuWiki proxy

    """

    def __init__(self, url: str = WIKI_URL, user: str = USER, password=PSWD):
        self._url = url
        self._wiki = None
        self._connected = False
        try:
            self._wiki = DokuWiki(url, user, password)
        except DokuWikiError as e:
            logger.error(f'Connecting to {url} failed: {e}')
        except Exception as e:
            logger.error(f'Connecting to {url} failed: {e}')
        if self._wiki is None:
            raise DokuWikiError(f'Failed to connect to {url}')
        else:
            self._connected = True
            logger.info(f'Connected to {self._url}')
            logger.info(f'Dokuwiki version: {self._wiki.version}')
            logger.info(f'XMLRPC version: {self._wiki.xmlrpc_version}')

    def is_connected(self) -> bool:
        """True if a connection to the ocxwiki is established, False otherwise."""
        return self._connected

    def current_url(self) -> str:
        """Return the current ocxwiki url."""
        return self._url

    def login(self, user: str = USER, password: str = PSWD) -> bool:
        """Log in to the wiki.

        Args:
            user: the wiki user
            password: The user password
        """

        try:
            self._wiki.login(user, password)
            self._connected = True
            return True
        except (DokuWikiError, Exception) as err:
            logger.error(f'Unable to connect: {err}')
            self._connected = False
        return self._connected

    def wiki_version(self) -> str:
        """Return the ocxwiki dokuwiki version."""
        return self._wiki.version

    def xmlrpc_version(self) -> str:
        """Return the ocxwiki xmlrpc version."""
        return self._wiki.xmlrpc_version

    # Wiki pages
    def list_pages(self, namespace: str = DEFAULT_NSP, depth: int = 0, md5_hash: bool = False, skip_acl: bool = False):
        """List all pages.

        Arguments:
            depth: recursion level, 0 for all
            md5_hash: do an md5 sum of content
            skip_acl: skip everything regardless of ACL
            namespace: List pages in this namespace.
            """
        options = {'depth': depth, 'hash': md5_hash, 'skipacl': skip_acl}
        return self._wiki.pages.list(namespace, **options)

    def changes(self, timestamp: datetime):
        """Returns a list of changes since given timestamp.

        Arguments:
            timestamp: input time

        Returns:
            Returns a list of changes since given timestamp.
            """
        return self._wiki.pages.changes(timestamp)

    def append_page(self, page: str, content: str, summary: str, namespace: str = DEFAULT_NSP,
                    minor: bool = False):
        """Appends content to ''page''.

        Arguments:
            page: page name
            namespace: the namespace of the page
            content: content to be appended to the page
            summary: Change summary
            minor: Whether this is a minor change


        Returns:

            """
        wiki_page = f'{namespace}:{page}'
        result = False
        try:
            result = self._wiki.pages.append(wiki_page, content, summary, minor)
        except DokuWikiError as e:
            logger.error(e)
        return result

    def set_page(self, page: str, content: str, summary: str, namespace: str = DEFAULT_NSP,
                 minor: bool = False) -> bool:
        """Set/replace the content of ''page''.

        Arguments:
            page: page name
            namespace: the namespace of the page
            content: content to be appended to the page
            summary: Change summary
            minor: Whether this is a minor change


        Returns:
            Returns True if the page was successfully set, False otherwise.
            """
        options = {'sum': summary, 'minor': minor}
        wiki_page = f'{namespace}:{page}'
        result = False
        try:
            result = self._wiki.pages.set(wiki_page, content, **options)
        except DokuWikiError as e:
            logger.error(e)
        return result

    # Data structs
    def get_data(self, page: str, keep_order: bool = True) -> Dict:
        """Get the structured data of the latest version of a given page.

        Arguments:
            page: the page of interest
            keep_order: Return an ordered dict if True
            """
        # Get the page content
        data = {}
        try:
            content = self._wiki.pages.get(page)
            data = struct_data.struct_get(content, keep_order)
        except DokuWikiError as e:
            logger.error(e)
        return data

    # Wiki media
    def list_media(self, namespace: str, depth: int = 0, md5_hash: bool = False, skip_acl: bool = False,
                   pattern: str = '*') -> Dict:
        """List the wiki media.

        Arguments:
            namespace: List media in namespace
            depth: recursion level, 0 for all
            md5_hash: do an md5 sum of content
            skip_acl: skip everything regardless of ACL
            pattern: list only media matching pattern
            """
        options = {'depth': depth, 'hash': md5_hash, 'skipacl': skip_acl}
        result = {}
        try:
            result = self._wiki.medias.list(namespace, **options)
        except DokuWikiError as e:
            logger.error(e)
        return result

    def media_changes(self, timestamp: datetime):
        """Returns the list of medias changed since given ''timestamp''.

        Arguments:
            timestamp: input time

        Returns:
            Returns a list of changes since given ''timestamp''.
            """
        return self._wiki.medias.changes(timestamp)

    def media_info(self, media: str):
        """Returns information of ''media''.

        Arguments:
            media: name of media

        Returns:
            Returns information of ''media''.
            """
        return self._wiki.medias.info(media)

    def add_media(self, media: str, filepath: Path, overwrite: bool = True):
        """Set media from local file filepath.

        Arguments:
            media: name of media
            filepath: path to local media file
            overwrite: parameter specify if the media must be replaced if it exists remotely.

            """

        self._wiki.medias.add(media, filepath.resolve(), overwrite)

    def media_delete(self, media: str):
        """Delete ''media''.

        Arguments:
            media: name of media

           """
        return self._wiki.medias.delete(media)
