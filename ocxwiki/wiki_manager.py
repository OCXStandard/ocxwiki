#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""Manage ocxwiki pages."""

# System imports
from pathlib import Path
from enum import Enum
from typing import Dict, OrderedDict, List, Tuple, Union, Optional
import re
from dataclasses import dataclass, field

# Third party imports
from loguru import logger
import datetime
from lxml.etree import QName

import pregex.meta as me
from pregex.core import *

# Module imports
import ocx_schema_parser
from ocx_schema_parser.xelement import LxmlElement
from ocx_schema_parser.transformer import Transformer
from ocx_schema_parser.elements import OcxGlobalElement
from ocx_schema_parser.data_classes import OcxEnumerator, SchemaAttribute
import ocxwiki
from ocxwiki.client import WikiClient
from ocxwiki.renderer import Render
from ocxwiki.error import OcxWikiError
from ocxwiki.struct_data import WikiSchema

class PublishState(Enum):
    DRAFT = 0
    PUBLIC = 1

class WikiManager:

    def __init__(self, wiki_url: str, user:str, pswd:str, schema_url:str):
        """Manage updates of ocxwiki pages.
        Arguments:
            wiki_url: ocxwiki url
            user: The wiki user
            pswd: The user password
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
        self.client: WikiClient = WikiClient(wiki_url, user, pswd)
        self.transformer: Union[Transformer, None] = None
        self._wiki_user = user
        self._schema_url = schema_url
        self._state:PublishState  = PublishState.DRAFT
        self._publish_ns = {PublishState.PUBLIC: 'public', PublishState.DRAFT: 'ocx-if:draft'}
        self._wiki_schema: Union[WikiSchema, None] = None
        self._ocx_elements: List[Tuple] = []
        self._xs_types:Dict = {}

    def schema_url(self) -> str:
        """Returns the url to the current OCX schema."""
        return self._schema_url

    def get_schema_locations(self) -> Dict:
        """Return the schema locations, also referenced schemas."""

        return self.transformer.get

    def process_schema(self, url: str, download_folder: Path) -> bool:
        """Process the schema given by the url.
        Arguments:
            url: Schema url

        """
        # Create a fresh schema transformer
        if self.transformer is not None:
            del self.transformer
        self.transformer = Transformer()
        result =  self.transformer.transform_schema_from_url(url,download_folder)
        if result:
             self.transform()
        return result

    def process_schema_folder(self, folder: Path)->bool:
        """Process the schema in the ```folder```.
        Arguments:
            folder: The folder containing the schema

        """
        # Create a fresh schema transformer
        if self.transformer is not None:
            del self.transformer
        self.transformer = Transformer()
        result =  self.transformer.transform_schema_from_folder(folder)
        if result:
             self.transform()
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
                if type in builtins:
                    child.type = Render.link_external(type, builtins)
                else:
                    pattern = cl.AnyWhitespace() + qu.Exactly(type, 1) + cl.AnyWhitespace()
                    if len(pattern.get_matches(type)) > 0:
                        child.type = pattern.replace(type, f' [[{publish_ns}:{prefix}:{name}]] ')
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
                if attribute.type in builtins:
                    attribute.type = Render.link_external(type, builtins)
                else:
                    pattern = cl.AnyWhitespace() + qu.Exactly(type, 1) + cl.AnyWhitespace()
                    if len(pattern.get_matches(type)) >0:
                        attribute.type = pattern.replace(type, f' [[{publish_ns}:{prefix}:{name}]] ')

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

    def set_publish_state(self, state: PublishState = PublishState.DRAFT):
        """Set draft mode to True or False.

        Arguments:
            mode: the draft mode (True or False)
            """
        self._state = state


    def get_publish_state(self) -> PublishState:
        """Publish state.
        Returns:
            The current publish state, either DRAFT or PUBLIC
        """
        return self._state


    def get_publish_namespace(self) -> str:
        """Return the publishing name space.
        Returns:
            namespace: Either ``draft`` ior``public`` depending on teh ``PublishState``.

        """
        return self._publish_ns[self._state]

    def get_wiki_data_struct(self) -> WikiSchema:
        """Return the current ``WikiSchema`` data."""
        return self._wiki_schema

    def connect(self, user: str, pswd:str) -> bool:
        """Connect to the wiki."""
        return self.client.login(user, pswd)

