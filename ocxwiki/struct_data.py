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
def struct_gen(name, data):
    """Generate dataentry *name* from *data*."""
    return '---- dataentry %s ----\n%s\n----' % (name, '\n'.join(
        '%s:%s' % (attr, value) for attr, value in data.items()))


@staticmethod
def struct_ignore(content):
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

    Arguments:

    """
    version: str = field(metadata={"header": "Schema Version"})
    namespace: str = field(metadata={"header": "Namespace URI"})
    author: str = field(metadata={"header": "Author"})
    date: str = field(metadata={"header": "Date"})
    status: str = field(default="", metadata={"header": "Status"})
