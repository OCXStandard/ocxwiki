#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""Manage ocxwiki pages."""

# System imports
from pathlib import Path
from enum import Enum
from typing import Dict, OrderedDict, List, Tuple, Union, Optional
import re
from dataclasses import dataclass, field
import asyncio

# Third party imports
from loguru import logger
import datetime
from lxml.etree import QName

# Module imports
from ocx_schema_parser.xelement import LxmlElement
from ocx_schema_parser.transformer import Transformer
from ocx_schema_parser.elements import OcxGlobalElement
from ocx_schema_parser.data_classes import OcxEnumerator, SchemaAttribute
import ocxwiki
from ocxwiki.client import WikiClient
from ocxwiki.render import Render
from ocxwiki.error import OcxWikiError
from ocxwiki.struct_data import WikiSchema

class PublishState(Enum):
    DRAFT = 0
    PUBLIC = 1

class WikiManager:

    def __init__(self, wiki_url,  schema_url:str = None):
        """Manage updates of ocxwiki pages.
        Arguments:
            wiki_url: ocxwiki url
            schema_url: The url of the OCX schema

        Parameters:
            self.client: The wiki client
            self.reader: The schema reader
            self._schema: The url to the OCX schema
            self._draft: Whether the schema is in draft or published mode. Default is draft mode (True)
            self._ocx_elements: List of schema global elements
            self._xs_types: dict of XML schema builtins
            self._wiki_user: Wiki login username

        """
        self._client: WikiClient = WikiClient(url=wiki_url)
        self._transformer: Union[Transformer, None] = None
        self._schema_url = schema_url
        self._state:PublishState  = PublishState.DRAFT
        self._publish_ns = {PublishState.PUBLIC: 'public:schema:', PublishState.DRAFT: 'ocx-if:draft-schema'}
        self._wiki_schema: Union[WikiSchema, None] = None
        self._ocx_elements: List[Tuple] = []
        self._xs_types:Dict = {}
        self._wiki_user: str = "Unknown"  # Default user, will be set when connecting to wiki

    @property
    def transformer(self) -> Union[Transformer, None]:
        """Return the schema transformer."""
        return self._transformer

    @property
    def client(self) -> WikiClient:
        """Return the wiki client."""
        return self._client

    def schema_url(self) -> str:
        """Returns the url to the current OCX schema."""
        return self._schema_url


    def process_schema(self, url: str, download_folder: Path) -> bool:
        """Process the schema given by the url.
        Arguments:
            url: Schema url

        """
        # Create a fresh schema transformer
        if self._transformer is not None:
            del self._transformer
        self._transformer = Transformer()
        logger.debug(f'Processing schema from url: {url} with download folder: {download_folder}')
        result =  self.transformer.transform_schema_from_url(url,download_folder)
        if result:
            self.transform()
            if self.transformer:
                logger.debug(f'Transformed schema version: {self.transformer.parser.get_schema_version()}')
            else:
                logger.debug('No transformer available after processing schema.')
        return result

    def process_schema_folder(self, folder: Path)->bool:
        """Process the schema in the ```folder```.
        Arguments:
            folder: The folder containing the schema

        """
        # Create a fresh schema transformer
        if self.transformer is not None:
            del self._transformer
        self._transformer = Transformer()
        logger.debug(f'Processing schema from url: {folder}')
        result =  self.transformer.transform_schema_from_folder(folder)
        if result:
             self.transform()
             if self.transformer:
                logger.debug(f'Transformed schema version: {self.transformer.parser.get_schema_version()}')
        return result


    def transform(self):
        """Transform the schema to python objects.

        Args:
            self:
        """
        # Build the known schema names providing the basis for the wiki page linking
        # w3c builtins
        namespaces = self.transformer.parser.get_namespaces()
        builtins = self.transformer.parser.get_xs_types()
        for key in builtins:
            qns = QName(key).namespace
            qname = QName(key).localname
            link = builtins[key]
            prefix = self.transformer.parser.get_prefix_from_namespace(qns)
            self._xs_types[f'{prefix}:{qname}'] = link
            # xsd and xs types are complementary
            if prefix == 'xs':
                self._xs_types[f'xsd:{qname}'] = link
            elif prefix == 'xsd':
                self ._xs_types[f'xs:{qname}'] = link
        version = self.transformer.parser.get_schema_version()
        author = self._wiki_user
        date = datetime.datetime.now().strftime("%b %d %Y %H:%M:%S")
        target_namespace = self.transformer.parser.get_schema_namespace(version)
        publish_ns = self.get_publish_namespace()
        parser_version = ocxwiki.__version__
        self._wiki_schema = WikiSchema(author=author, namespace=target_namespace, ocx_location=target_namespace,
                                       ocx_version=version,
                                       date=date, status=str(self._state), wiki_version= parser_version)
        # The known schema types
        for ocx in self.transformer.parser.get_schema_element_types():
            qn = LxmlElement.replace_ns_tag_with_ns_prefix(ocx, namespaces)
            self._ocx_elements.append((LxmlElement.namespace_prefix(qn), LxmlElement.strip_namespace_prefix(qn)))
        for ocx in self.transformer.parser.get_schema_attribute_types():
            qn = LxmlElement.replace_ns_tag_with_ns_prefix(ocx, namespaces)
            self._ocx_elements.append(((LxmlElement.namespace_prefix(qn), LxmlElement.strip_namespace_prefix(qn))))
        for ocx in self.transformer.parser.get_schema_attribute_group_types():
            qn = LxmlElement.replace_ns_tag_with_ns_prefix(ocx, namespaces)
            self._ocx_elements.append(((LxmlElement.namespace_prefix(qn), LxmlElement.strip_namespace_prefix(qn))))
        for ocx in self.transformer.parser.get_schema_simple_types():
            qn = LxmlElement.replace_ns_tag_with_ns_prefix(ocx, namespaces)
            self._ocx_elements.append(((LxmlElement.namespace_prefix(qn), LxmlElement.strip_namespace_prefix(qn))))
        # Add enums to the global name list
        for name, enum in self.transformer.get_enumerators().items():
            name = enum.name
            prefix = enum.prefix
            self._ocx_elements.append((prefix, name))
        # ToDo: fix missing link to id
        self.apply_wiki_links(self._ocx_elements, self._xs_types, publish_ns)

    def apply_wiki_links(self, global_elements: List, builtins: Dict, publish_ns: str)-> None:
        """Apply wiki page links and external links.

        Args:
            global_elements: All OCX globals element names
            builtins: W3C types
            publish_ns: The wiki namespace

        """

        for ocx in self.transformer.get_ocx_elements():
            # Apply wiki page links to OCX globals
            for child in ocx.get_children():
                name = child.name
                prefix = child.prefix
                type = child.type
                child.name = Render.link_internal(prefix, name, publish_ns)
                # Link to any builtins
                if type and type in builtins:
                    child.type = Render.link_external(type, builtins)
                elif type:
                    # Create internal wiki link for non-builtin types
                    # Check if type corresponds to a known element
                    type_parts = type.split(':') if ':' in type else [prefix, type]
                    if len(type_parts) == 2:
                        type_prefix, type_name = type_parts
                        child.type = f'[[{publish_ns}:{type_prefix}:{type_name}]]'
            # Apply links to attributes
            for attribute in ocx.get_attributes():
                name = attribute.name
                prefix = attribute.prefix
                type = attribute.type
                # Internal page links
                search = filter(lambda x: x[1]==name, global_elements)
                for item in search:
                    attribute.name = Render.link_internal(prefix, name, publish_ns)
                # External links
                if attribute.type and attribute.type in builtins:
                    attribute.type = Render.link_external(type, builtins)
                elif type:
                    # Create internal wiki link for non-builtin types
                    # Check if type corresponds to a known element
                    type_parts = type.split(':') if ':' in type else [prefix, type]
                    if len(type_parts) == 2:
                        type_prefix, type_name = type_parts
                        attribute.type = f'[[{publish_ns}:{type_prefix}:{type_name}]]'

        return

    def publish_page(self, ocx: OcxGlobalElement) -> bool:
        """Publish a dokuwiki page with ``name`` to the ocxwiki. This will create a new version of the page in the
            ``publish`` namespace.

        Arguments:
            ocx: The documentation of the OCX element to add to the dokuwiki

        Returns:
            True if successfully, false otherwise.
        """
        if self.transformer is None:
            raise OcxWikiError('No schema url has been processed.')
        wiki_namespace = self.get_publish_namespace()
        page_name = f'{ocx.get_prefix()}:{ocx.get_name()}'
        ocx_namespace = QName(ocx.get_tag()).namespace
        self._wiki_schema.namespace = ocx_namespace
        content = Render.page(ocx, self._wiki_schema, self._ocx_elements, self._xs_types)
        # add internal and external links
        #content = Render.links(content, self._ocx_elements, self._xs_types, namespace)
        summary = f'Publish schema version {self._wiki_schema.ocx_version}'
        result = self.client.set_page(page_name, content, summary, wiki_namespace, False)
        return result

    async def publish_page_async(self, ocx: OcxGlobalElement) -> bool:
        """Async version of publish_page. Publish a dokuwiki page with ``name`` to the ocxwiki.

        Arguments:
            ocx: The documentation of the OCX element to add to the dokuwiki

        Returns:
            True if successfully, false otherwise.
        """
        if self.transformer is None:
            raise OcxWikiError('No schema url has been processed.')
        wiki_namespace = self.get_publish_namespace()
        page_name = f'{ocx.get_prefix()}:{ocx.get_name()}'
        ocx_namespace = QName(ocx.get_tag()).namespace
        self._wiki_schema.namespace = ocx_namespace
        content = Render.page(ocx, self._wiki_schema, self._ocx_elements, self._xs_types)
        summary = f'Publish schema version {self._wiki_schema.ocx_version}'
        result = await self.client.set_page_async(page_name, content, summary, wiki_namespace, False)
        return result


    def publish_enum(self, enum: OcxEnumerator) -> bool:
        """Publish a schema enum page with ``name`` to the ocxwiki. This will create a new version of the page in the
            ``publish`` namespace.

        Arguments:
            enum: The schema enumerator

        Returns:
            True if successfully, false otherwise.
        """
        if self.transformer is None:
            raise OcxWikiError('No schema url has been processed.')
        namespace = self.get_publish_namespace()
        page_name = f'{enum.prefix}:{enum.name}'
        content = Render.enum(enum, self._wiki_schema)
        summary = 'Bumped schema version'
        return self.client.set_page(page_name, content, summary, namespace, False)

    async def publish_enum_async(self, enum: OcxEnumerator) -> bool:
        """Async version of publish_enum. Publish a schema enum page to the ocxwiki.

        Arguments:
            enum: The schema enumerator

        Returns:
            True if successfully, false otherwise.
        """
        if self.transformer is None:
            raise OcxWikiError('No schema url has been processed.')
        namespace = self.get_publish_namespace()
        page_name = f'{enum.prefix}:{enum.name}'
        content = Render.enum(enum, self._wiki_schema)
        summary = 'Bumped schema version'
        return await self.client.set_page_async(page_name, content, summary, namespace, False)

    def publish_simple_type(self, attribute: SchemaAttribute) -> bool:
        """Publish a schema simpleType page with ``name`` to the ocxwiki. This will create a new version of the page in the
            ``publish`` namespace.

        Arguments:
            attribute: The attribute to publish

        Returns:
            True if successfully, false otherwise.
        """
        if self.transformer is None:
            raise OcxWikiError('No schema url has been processed.')
        namespace = self.get_publish_namespace()
        page_name = f'{attribute.prefix}:{attribute.name}'
        content = Render.attribute(attribute, self._wiki_schema)
        # add internal and external links
        #content = Render.links(content, self._ocx_elements, self._xs_types, namespace)
        summary = 'Bumped schema version'
        return self.client.set_page(page_name, content, summary, namespace, False)

    async def publish_simple_type_async(self, attribute: SchemaAttribute) -> bool:
        """Async version of publish_simple_type. Publish a schema simpleType page to the ocxwiki.

        Arguments:
            attribute: The attribute to publish

        Returns:
            True if successfully, false otherwise.
        """
        if self.transformer is None:
            raise OcxWikiError('No schema url has been processed.')
        namespace = self.get_publish_namespace()
        page_name = f'{attribute.prefix}:{attribute.name}'
        content = Render.attribute(attribute, self._wiki_schema)
        summary = 'Bumped schema version'
        return await self.client.set_page_async(page_name, content, summary, namespace, False)

    def publish_attribute(self, attribute: SchemaAttribute) -> bool:
        """Publish a schema global attribute page with ``name`` to the ocxwiki. This will create a new version of the page in the
            ``publish`` namespace.

        Arguments:
            attribute: The attribute to publish

        Returns:
            True if successfully, false otherwise.
        """
        if self.transformer is None:
            raise OcxWikiError('No schema url has been processed.')
        namespace = self.get_publish_namespace()
        page_name = f'{attribute.prefix}:{attribute.name}'
        content = Render.attribute(attribute, self._wiki_schema)
        summary = 'Bumped schema version'
        result = self.client.set_page(page_name, content, summary, namespace, False)
        return result

    async def publish_attribute_async(self, attribute: SchemaAttribute) -> bool:
        """Async version of publish_attribute. Publish a schema global attribute page to the ocxwiki.

        Arguments:
            attribute: The attribute to publish

        Returns:
            True if successfully, false otherwise.
        """
        if self.transformer is None:
            raise OcxWikiError('No schema url has been processed.')
        namespace = self.get_publish_namespace()
        page_name = f'{attribute.prefix}:{attribute.name}'
        content = Render.attribute(attribute, self._wiki_schema)
        summary = 'Bumped schema version'
        result = await self.client.set_page_async(page_name, content, summary, namespace, False)
        return result

    def set_publish_state(self, state: PublishState = PublishState.DRAFT):
        """Set the publish state to DRAFT or PUBLIC.

        Arguments:
            state: the publish state (PublishState.DRAFT or PublishState.PUBLIC)
            """
        self._state = state
        if self._wiki_schema is not None:
            self._wiki_schema.status = str(state)


    def get_publish_state(self) -> PublishState:
        """Publish state.
        Returns:
            The current publish state, either DRAFT or PUBLIC
        """
        return self._state


    def get_publish_namespace(self) -> str:
        """Return the publishing name space.
        Returns:
            namespace: Either ``draft`` or``public`` depending on teh ``PublishState``.

        """
        if self._state == PublishState.PUBLIC and self.transformer:
            version = self.transformer.parser.get_schema_version()       # Add ocx version to public namespace
            return f'{self._publish_ns[self._state]}{version}'
        else:
            return self._publish_ns[self._state]

    def get_wiki_data_struct(self) -> WikiSchema:
        """Return the current ``WikiSchema`` data."""
        return self._wiki_schema

    def connect(self, user: str, pswd:str) -> bool:
        """Connect to the wiki."""
        result = self.client.connect(user=user, password=pswd)
        if result:
            self._wiki_user = user
        return result

    async def connect_async(self, user: str, pswd: str) -> bool:
        """Async version of connect. Connect to the wiki."""
        result = await self.client.connect_async(user=user, password=pswd)
        if result:
            self._wiki_user = user
        return result

    async def publish_all_pages_async(self, pages: List[OcxGlobalElement],
                                     max_concurrent: int = 10,
                                     progress_callback: Optional[callable] = None) -> List[bool]:
        """Publish multiple pages concurrently.

        Arguments:
            pages: List of OCX global elements to publish
            max_concurrent: Maximum number of concurrent publish operations
            progress_callback: Optional callable(advance, total, description) for progress updates

        Returns:
            List of results (True/False) for each page
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def publish_with_semaphore(page):
            async with semaphore:
                result = await self.publish_page_async(page)
                if progress_callback is not None:
                    try:
                        progress_callback(1, None, f'Page: {page.get_name()}')
                    except Exception:
                        pass
                return result

        tasks = [publish_with_semaphore(page) for page in pages]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def publish_all_enums_async(self, enums: Dict[str, OcxEnumerator],
                                     max_concurrent: int = 10,
                                     progress_callback: Optional[callable] = None) -> List[bool]:
        """Publish multiple enums concurrently.

        Arguments:
            enums: Dictionary of enums to publish
            max_concurrent: Maximum number of concurrent publish operations
            progress_callback: Optional callable(advance, total, description) for progress updates

        Returns:
            List of results (True/False) for each enum
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def publish_with_semaphore(enum):
            async with semaphore:
                result = await self.publish_enum_async(enum)
                if progress_callback is not None:
                    try:
                        progress_callback(1, None, f'Enum: {enum.name}')
                    except Exception:
                        pass
                return result

        tasks = [publish_with_semaphore(enum) for enum in enums.values()]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def publish_all_attributes_async(self, attributes: List[SchemaAttribute],
                                          max_concurrent: int = 10,
                                          progress_callback: Optional[callable] = None) -> List[bool]:
        """Publish multiple attributes concurrently.

        Arguments:
            attributes: List of attributes to publish
            max_concurrent: Maximum number of concurrent publish operations
            progress_callback: Optional callable(advance, total, description) for progress updates

        Returns:
            List of results (True/False) for each attribute
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def publish_with_semaphore(attr):
            async with semaphore:
                result = await self.publish_attribute_async(attr)
                if progress_callback is not None:
                    try:
                        progress_callback(1, None, f'Attribute: {attr.name}')
                    except Exception:
                        pass
                return result

        tasks = [publish_with_semaphore(attr) for attr in attributes]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def publish_all_simple_types_async(self, simple_types: List[SchemaAttribute],
                                            max_concurrent: int = 10,
                                            progress_callback: Optional[callable] = None) -> List[bool]:
        """Publish multiple simple types concurrently.

        Arguments:
            simple_types: List of simple types to publish
            max_concurrent: Maximum number of concurrent publish operations
            progress_callback: Optional callable(advance, total, description) for progress updates

        Returns:
            List of results (True/False) for each simple type
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def publish_with_semaphore(simple_type):
            async with semaphore:
                result = await self.publish_simple_type_async(simple_type)
                if progress_callback is not None:
                    try:
                        progress_callback(1, None, f'SimpleType: {simple_type.name}')
                    except Exception:
                        pass
                return result

        tasks = [publish_with_semaphore(st) for st in simple_types]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def publish_complete_schema_async(self, max_concurrent: int = 10,
                                           progress_callback: Optional[callable] = None) -> Dict[str, Union[int, List]]:
        """Publish the complete schema asynchronously.

        Arguments:
            max_concurrent: Maximum number of concurrent publish operations
            progress_callback: Optional callable(advance, total, description) called after each
                published item. ``advance`` is always 1; ``total`` is set once at the start
                with the grand total so the TUI can initialise the progress bar.

        Returns:
            Dictionary with counts of published items
        """
        if self.transformer is None:
            raise OcxWikiError('No schema url has been processed.')
        if not self._client.is_connected():
            raise OcxWikiError('Not connected to the wiki. Call connect() first.')

        results = {
            'pages': 0,
            'enums': 0,
            'attributes': 0,
            'simple_types': 0,
            'errors': []
        }

        # Calculate grand total so the TUI can initialise the progress bar
        pages = self.transformer.get_ocx_elements()
        enums = self.transformer.get_enumerators()
        attributes = self.transformer.get_global_attributes()
        simple_types = self.transformer.get_simple_types()
        grand_total = len(pages) + len(enums) + len(attributes) + len(simple_types)

        if progress_callback is not None:
            try:
                # Signal the total using advance=0 and total=grand_total
                progress_callback(0, grand_total, 'Starting…')
            except Exception:
                pass

        # Publish all pages
        page_results = await self.publish_all_pages_async(pages, max_concurrent, progress_callback)
        results['pages'] = sum(1 for r in page_results if r is True)
        results['errors'].extend([r for r in page_results if isinstance(r, Exception)])

        # Publish all enums
        enum_results = await self.publish_all_enums_async(enums, max_concurrent, progress_callback)
        results['enums'] = sum(1 for r in enum_results if r is True)
        results['errors'].extend([r for r in enum_results if isinstance(r, Exception)])

        # Publish all attributes
        attr_results = await self.publish_all_attributes_async(attributes, max_concurrent, progress_callback)
        results['attributes'] = sum(1 for r in attr_results if r is True)
        results['errors'].extend([r for r in attr_results if isinstance(r, Exception)])

        # Publish all simple types
        st_results = await self.publish_all_simple_types_async(simple_types, max_concurrent, progress_callback)
        results['simple_types'] = sum(1 for r in st_results if r is True)
        results['errors'].extend([r for r in st_results if isinstance(r, Exception)])

        results['total'] = grand_total
        return results



