#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""Manage ocxwiki pages."""

# System imports
from typing import Dict, OrderedDict
import re
from dataclasses import dataclass, field

# Third party imports
from loguru import logger
from ocx_schema_parser.data_classes import BaseDataClass
from ocx_schema_parser.parser import OcxSchema

# Module imports
from ocxwiki import WIKI_URL, USER, PSWD
from ocxwiki.client import WikiClient


class WikiManager:
    """Manage updates of ocxwiki pages."""
    def __init__(self, url: str = WIKI_URL):
        self._client = WikiClient(url, USER, PSWD)
