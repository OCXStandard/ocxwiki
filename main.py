#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
# For debug purpose

from collections import defaultdict
import arrow
from rich import print
from pathlib import Path
from tabulate import tabulate

from ocxwiki import WORKING_DRAFT, SCHEMA_FOLDER, WIKI_URL, TEST_WIKI_URL, USER, TEST_PSWD, PSWD
from ocxwiki.wiki_manager import WikiManager


def ocx(manager, interactive: bool = True, element: str= 'ocx:SectionRef'):

    ocx = manager.transformer.get_ocx_element_from_type(element)
    if ocx is not None:
        success =  manager.publish_page(ocx)
        if success:
            print(f'Published page {element}')
        else:
            print(f'Failed publishing {element}')

