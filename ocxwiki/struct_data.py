#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE

"""Manage structured data on wiki pages."""

# System imports
from typing import Dict, OrderedDict
import re
from dataclasses import dataclass, field

# Third party imports
from loguru import logger
from ocx_schema_parser.data_classes import BaseDataClass
# Module imports


from ocxwiki.error import OcxWikiError


@staticmethod
def struct_get(content, keep_order=False) -> Dict:
    """Get dataentry from *content*. *keep_order* indicates whether to
    return an ordered dictionnay."""
    if keep_order:
        from collections import OrderedDict
        dataentry = OrderedDict()
    else:
        dataentry = {}

    found = False
    for line in content.split('\n'):
        if line.strip().startswith('---- dataentry'):
            found = True
            continue
        elif line == '----':
            break
        elif not found:
            continue

        line_split = line.split(':')
        key = line_split[0].strip()
        value = re.sub('#.*$', '', ':'.join(line_split[1:])).strip()
        dataentry.setdefault(key, value)

    if not found:
        raise OcxWikiError('no dataentry found on the page')
    return dataentry


@staticmethod
def struct_gen(name: str, data: Dict) -> str:
    """Generate dataentry *name* from *data*."""
    struct =  f'---- dataentry {name} ----\n'
    for attr, value in data.items():
        struct += f'\n{attr} : {value}'
    struct +='\n----\n'
    return struct


@staticmethod
def struct_ignore(content: str) -> str:
    """Remove dataentry from *content*."""
    page_content = []
    start = False
    for line in content.split('\n'):
        if line == '----' and not start:
            start = True
            continue
        if start:
            page_content.append(line)
    return '\n'.join(page_content) if page_content else content


@dataclass
class WikiSchema(BaseDataClass):
    """Data class defining the structured data schema

        Parameters:
            ocx_version: OCX Schema version
            ocx_location: The uri of the schema location
            namespace: The schema type namespace
            author: Publishing author
            date: Publish date
            status: The schema status (draft or published)
            wiki_version: The wiki CLI version

    """
    ocx_version: str = field(metadata={"header": "OCX Version "})
    ocx_location: str = field(metadata={"header": "Location URL_url "})
    namespace: str = field(metadata={"header": "Namespace"})
    author: str = field(metadata={"header": "Author "})
    date: str = field(metadata={"header": "Date "})
    status: str = field(metadata={"header": "Statuss "}) # For some strange reason the last character disappear when rendered on the wiki
    wiki_version:str = field(metadata={"header": "Publisher version "})
