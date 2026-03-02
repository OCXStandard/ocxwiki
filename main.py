#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
# For debug purpose

from collections import defaultdict
import arrow
from rich import print
from pathlib import Path
from tabulate import tabulate

from ocxwiki import WORKING_DRAFT, SCHEMA_FOLDER, WIKI_URL, TEST_WIKI_URL, USER, TEST_PSWD, PSWD
from ocxwiki.wiki_manager import WikiManager


manager = WikiManager(
    wiki_url=WIKI_URL)

def ocx_children(manager,element: str= 'ocx:Plate'):

    manager.connect(USER, PSWD)
    if manager.client.is_connected():
        print(f"Connected to wiki")
        manager.process_schema(url=WORKING_DRAFT, download_folder=Path(SCHEMA_FOLDER))
        ocx = manager.transformer.get_ocx_element_from_type(element)
        if ocx is not None:
            children = ocx.get_children()
            for child in children:
                print(f'Child: {child.name[1]}')
    else:
        print(f"Failed to connect to wiki")
        return


if __name__ == "__main__":
    ocx_children(manager)