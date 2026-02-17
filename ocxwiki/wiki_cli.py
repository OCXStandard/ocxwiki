#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""This module provides the ocxwiki app functionality."""


# Sys imports
import sys
from collections import defaultdict
# Third party imports
from loguru import logger
import arrow
import typer
from rich import print
from rich.progress import track
from pathlib import Path
from typing_extensions import Annotated

# Module imports
from ocxwiki import __app_name__, __version__, WIKI_URL, WORKING_DRAFT, USER, TEST_PSWD, PSWD, TEST_WIKI_URL, \
    SCHEMA_FOLDER
from ocxwiki.wiki_manager import WikiManager, PublishState
from tabulate import tabulate

wiki = typer.Typer()
wiki_manager = WikiManager(WIKI_URL, USER, PSWD, WORKING_DRAFT)

# rich markup
MK_COLOR = 'blue'
MK_EMP = 'bold'
MK_ERR = 'red'

def markup(emphasis:str = MK_EMP, color:str = MK_COLOR) -> str:
    """Rich markup"""
    return f'[{emphasis} {color}]'

def markup_end(emphasis:str = MK_EMP, color:str = MK_COLOR) -> str:
    """Rich markup end"""
    return f'[/{emphasis} {color}]'

# def validate_ocx_callback(name: str) -> str:
#     if wiki_manager.transformer.get_ocx_element_from_type(name) is None:
#         print(f'The name {name} is not a valid schema element.')
#
#         typer.prompt(f'')

@wiki.command()
def process_schema_url(
        url: Annotated[str, typer.Option(help='Process a schema for publishing.', prompt=True)] = WORKING_DRAFT,
        folder: Annotated[Path, typer.Option(help='The schema download folder.')] = Path(SCHEMA_FOLDER),
    ):
    """Process a schema before publishing."""
    global result
    if wiki_manager:
        if result := wiki_manager.process_schema(url, folder): #ToDo: Fix error when processing a local file
            schema_summary()

@wiki.command()
def process_schema_folder(
        folder: Annotated[Path, typer.Option(help='The schema download folder.', prompt=True)] = Path(SCHEMA_FOLDER),
    ):
    """Process a schema before publishing."""
    if wiki_manager:
        result =  wiki_manager.process_schema_folder(folder)
        if result:
            schema_summary()

@wiki.command()
def schema_summary():
    """Print a summary of the processed schema."""
    if wiki_manager.transformer is not None:
        for ns, tbl in wiki_manager.transformer.parser.tbl_summary().items():
            print(f'Content of namespace {ns}:\n')
            print(tabulate(tbl, headers='keys'),'\n')
    else:
        print('Process a schema first')

@wiki.command()
def version():
    """Print the ocxwiki CLI version."""
    print(f'The {__app_name__} version: {__version__}')

@wiki.command()
def publish_all():
    """Publish the complete schema to the ocxwiki."""
    if wiki_manager.transformer is not None:
        wikiurl = wiki_manager.client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        version = wiki_manager.transformer.parser.get_schema_version()
        pages = len(wiki_manager.transformer.get_ocx_elements())
        pages += len(wiki_manager.transformer.get_global_attributes())
        pages += len(wiki_manager.transformer.get_simple_types())
        pages += len(wiki_manager.transformer.get_enumerators())
        msg = f'You are about to publish the schema version ' \
              f'{markup()}{version}{markup_end()}\nwith {markup()}{pages}{markup_end()} pages to namespace ' \
              f'{markup()}{namespace}{markup_end()} ' \
              f'to the ocxwiki with url {wikiurl}\n'
        print(msg)
        prompt = typer.confirm('OK to proceed?')

        if prompt:
            publish_ocx(interactive=False)
            publish_simple_types(interactive=False)
            publish_attributes(interactive=False)
            publish_enums(interactive=False)
            print(f'Published in total {pages} pages.')
    else:
        print('Process a schema first')

@wiki.command()
def publish_state(
        draft: Annotated[bool, typer.Option(
            help='The schema status, draft or public. True if the schema is a draft.',
            prompt=True)] = True

):
    """Set the publishing state (draft or public)."""
    publish_state = PublishState(not(draft))
    wiki_manager.set_publish_state(publish_state)
    print (wiki_manager.get_publish_state())

@wiki.command()
def list_pages(
         namespace: Annotated[str, typer.Option(
             help='All pages under the given namespace will be listed.',
             prompt=True)] = '/ocx-if:draft:ocx',

):
    """List the pages in the namespace"""
    result = wiki_manager.client.list_pages(namespace=namespace, md5_hash=False, skip_acl=True)
    tbl = defaultdict(list)
    for id, mtime, rev, *all  in result.items():
        tbl['Name'].append(str.replace(namespace,''))
        tbl['Revised'].append(arrow.get(mtime).format('YYYY-MM-DD HH:mm:ss ZZ'))
        tbl['Modified'].append(arrow.get(rev).format('YYYY-MM-DD HH:mm:ss ZZ'))
    print(tabulate(result, headers='keys'))

@wiki.command()
def publish_ocx(
    ocx: Annotated[str, typer.Argument(
        help='The name of the OCX element to publish.')] = 'All',
    interactive: Annotated[bool, typer.Option(
         help='Require a user confirmation before publishing.')] = True,
):
    """Publish a global schema element to the ocxwiki."""
    prompt = True
    pages = []
    if wiki_manager.transformer is not None:
        if ocx == 'All':
            pages = wiki_manager.transformer.get_ocx_elements()
        else:
            element = wiki_manager.transformer.get_ocx_element_from_type(ocx)
            if element is not None:
                pages = [element]
            else:
                print(f'No schema element with name {ocx}')
                return
        wikiurl = wiki_manager.client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        if interactive:
            msg = f'You are about to publish {markup()}{len(pages)}{markup_end()} pages in namespace ' \
                  f'{markup()}{namespace}{markup_end()} ' \
                  f'to the ocxwiki with url {wikiurl}\n'
            print(msg)
            prompt = typer.confirm('OK to proceed?')
        total = 0
        if prompt:
            for ocx in track(pages, description="Publishing global elements..."):
                wiki_manager.publish_page(ocx)
                total += 1
            print(f'Published {total} pages')
    else:
        print('Process a schema first')

@wiki.command()
def publish_attributes(
        interactive: Annotated[bool, typer.Option(
            help='Require a user confirmation before publishing.')] = True,

):
    """Publish all the global schema attributes to the ocxwiki."""
    prompt = True
    if wiki_manager.transformer is not None:
        attributes = wiki_manager.transformer.get_global_attributes()
        wikiurl = wiki_manager.client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        if interactive:
            msg = f'You are about to publish {markup()}{len(attributes)}{markup_end()} pages in namespace ' \
                  f'{markup()}{namespace}{markup_end()} ' \
                  f'to the ocxwiki with url {wikiurl}'
            print(msg)
            prompt = typer.confirm('OK to proceed?')
        total = 0
        if prompt:
            for attribute in track(attributes, description="Publishing attributes..."):
                wiki_manager.publish_attribute(attribute)
                total += 1
            print(f'Published {total} attribute pages')
    else:
        print('Process a schema first')

@wiki.command()
def publish_enums(
        interactive: Annotated[bool, typer.Option(
            help='Require a user confirmation before publishing.')] = True,
):
    """Publish the global schema enumerators to the ocxwiki."""
    prompt = True
    if wiki_manager.transformer is not None:
        enums = wiki_manager.transformer.get_enumerators()
        wikiurl = wiki_manager.client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        if interactive:
            msg = f'You are about to publish {markup()}{len(enums)}{markup_end()} enumerators in namespace ' \
                  f'{markup()}{namespace}{markup_end()} ' \
                  f'to the ocxwiki with url {wikiurl}'
            print(msg)
            prompt = typer.confirm('OK to proceed?')
        if prompt:
            total = 0
            for enum in track(enums, description="Publishing enumerators..."):
                wiki_manager.publish_enum(enums[enum])
                total += 1
            print(f'Published {total} enumerator pages')
    else:
        print('Process a schema first')


@wiki.command()
def publish_simple_types(
        interactive: Annotated[bool, typer.Option(
            help='Require a user confirmation before publishing.')] = True,

):
    """Publish the schema simple types to the ocxwiki."""
    prompt = True
    if wiki_manager.transformer is not None:
        simples = wiki_manager.transformer.get_simple_types()
        wikiurl = wiki_manager.client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        if interactive:
            msg = f'You are about to publish {markup()}{len(simples)}{markup_end()} simpleType elements in namespace ' \
                  f'{markup()}{namespace}{markup_end()} ' \
                  f'to the ocxwiki with url {wikiurl}'
            print(msg)
            prompt = typer.confirm('OK to proceed?')
        if prompt:
            total = 0
            for simple in track(simples, description="Publishing simpleType..."):
                wiki_manager.publish_simple_type(simple)
                total += 1
            print(f'Published {total} simpleType pages')
    else:
        print('Process a schema first')


@wiki.command()
def connect(
        user: Annotated[str, typer.Option(help='The ocxwiki user.', prompt=True, confirmation_prompt=True)] = USER,
):
    """Connect to the ocxwiki."""
    pswd = typer.prompt('Input the wiki user password', hide_input=True, confirmation_prompt=True)
    if connected := wiki_manager.client.login(user, pswd):
        print(f'Connected to {wiki_manager.client.current_url()}')
        print(f'Dokuwiki version: {wiki_manager.client.wiki_version()}')
        print(f'XMLRPC version: {wiki_manager.client.xmlrpc_version()}')



